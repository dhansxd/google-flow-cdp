"""Offline regressions for standalone Chrome inventory and session ownership."""
import ast
import contextlib
import io
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from flow_browser import FlowSession, list_profiles, next_profile
from flow_browser.session import OBSERVE
from flow_browser.input_guard import install


class InventoryTests(unittest.TestCase):
    def test_rotation_refreshes_accounts_skips_duplicates_and_wraps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = {'Default': {'user_name': 'first@example.invalid'},
                    'Profile 1': {'user_name': ' FIRST@example.invalid '},
                    'Profile 2': {'user_name': 'second@example.invalid'}}
            for key in rows:
                (root / key).mkdir()
            metadata = root / 'Local State'
            metadata.write_text(json.dumps({'profile': {'info_cache': rows}}))
            self.assertEqual(next_profile('Default', root).id, 'Profile 2')
            self.assertEqual(next_profile('Profile 2', root).id, 'Default')
            (root / 'Profile 2').rmdir()
            self.assertIsNone(next_profile('Default', root))
            (root / 'Profile 3').mkdir()
            rows['Profile 3'] = {'user_name': 'third@example.invalid'}
            metadata.write_text(json.dumps({'profile': {'info_cache': rows}}))
            self.assertEqual(next_profile('Default', root).id, 'Profile 3')

    def test_observation_handles_a_loading_document_without_body(self):
        program = "const document={body:null,title:'',readyState:'loading',images:[],querySelectorAll:()=>[]};const location={href:'about:blank'};console.log(JSON.stringify(" + OBSERVE + '));'
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['text'], '')

    def test_observation_includes_native_tabs_links_and_checkbox_state(self):
        program = r'''
const element = (tag, attributes) => ({
  tagName: tag, innerText: 'Control', checked: tag === 'INPUT',
  getClientRects: () => [1], getAttribute: name => attributes[name] ?? null
});
const controls = [element('MAT-LIST-ITEM', {role: 'tab', 'aria-selected': 'true'}),
                  element('A', {href: '/project/example'}), element('INPUT', {type: 'checkbox'})];
const document = {body: null, title: '', readyState: 'complete', images: [],
  querySelectorAll: selector => selector.includes('[role=tab]') ? controls : []};
const location = {href: 'about:blank'};
const getComputedStyle = () => ({visibility: 'visible'});
console.log(JSON.stringify(REPLACE_OBSERVATION));
'''.replace('REPLACE_OBSERVATION', OBSERVE)
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, check=True)
        controls = json.loads(result.stdout)['controls']
        self.assertEqual(controls[0]['selected'], 'true')
        self.assertEqual(controls[1]['href'], '/project/example')
        self.assertTrue(controls[2]['checked'])

    def test_add_delete_rename_and_recreated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Default').mkdir()
            rows = {'Default': {'name': 'First', 'user_name': 'first@example.invalid'}}
            metadata = root / 'Local State'
            metadata.write_text(json.dumps({'profile': {'info_cache': rows}}))
            first = list_profiles(root)[0]
            rows['Default']['name'] = 'Renamed'
            (root / 'Profile 2').mkdir()
            rows['Profile 2'] = {'name': 'Second'}
            metadata.write_text(json.dumps({'profile': {'info_cache': rows}}))
            current = list_profiles(root)
            self.assertEqual([item.id for item in current], ['Default', 'Profile 2'])
            self.assertEqual(current[0].identity, first.identity)
            self.assertEqual(current[0].name, 'Renamed')
            (root / 'Default').rmdir()
            self.assertEqual([item.id for item in list_profiles(root)], ['Profile 2'])
            (root / 'replacement').mkdir()
            (root / 'replacement').rename(root / 'Default')
            self.assertNotEqual(list_profiles(root)[0].identity, first.identity)

    def test_profile_inventory_rejects_links_and_special_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Default').mkdir()
            (root / 'Linked').symlink_to(root / 'Default')
            (root / 'System Profile').mkdir()
            rows = {name: {} for name in ('Default', 'Linked', 'System Profile', '../foreign')}
            (root / 'Local State').write_text(json.dumps({'profile': {'info_cache': rows}}))
            self.assertEqual([item.id for item in list_profiles(root)], ['Default'])


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.box = tempfile.TemporaryDirectory()
        self.root = Path(self.box.name)
        (self.root / 'Default').mkdir()
        self.metadata = self.root / 'Local State'
        self.rows = {'Default': {'name': 'First', 'user_name': 'first@example.invalid'}}
        self.save()
        self.sessions = []

    def save(self):
        self.metadata.write_text(json.dumps({'profile': {'info_cache': self.rows}}))

    def session(self):
        session = FlowSession(data=self.root, directory=self.root / str(len(self.sessions)))
        self.sessions.append(session)
        return session

    def tearDown(self):
        with patch('flow_browser.session.subprocess.run', return_value=Mock(returncode=0)):
            for session in self.sessions:
                session.close()
        self.box.cleanup()

    def test_each_session_has_an_independent_harness_endpoint_and_runtime(self):
        providers = [Mock(url='ws://session-a'), Mock(url='ws://session-b')]
        for provider in providers:
            provider.close.return_value = True
        with patch('flow_browser.session.ChromeSession', side_effect=providers), \
                patch.dict(os.environ, {'BU_CDP_WS': 'ws://foreign', 'BU_AUTOSPAWN': '1',
                                       'PYTHONPATH': '/foreign/python', 'PYTHONHOME': '/foreign/home',
                                       '__PYVENV_LAUNCHER__': '/foreign/python'}):
            first, second = self.session().open(), self.session().open()
        self.assertEqual(first.environment['BU_NAME'], 'default')
        self.assertEqual(second.environment['BU_NAME'], 'default')
        self.assertNotEqual(first.environment['BH_RUNTIME_DIR'], second.environment['BH_RUNTIME_DIR'])
        self.assertNotEqual(first.environment['BH_HOME'], second.environment['BH_HOME'])
        self.assertEqual(first.environment['BU_CDP_WS'], 'ws://session-a')
        self.assertNotIn('BU_AUTOSPAWN', list(first.environment))
        for key in ('PYTHONPATH', 'PYTHONHOME', '__PYVENV_LAUNCHER__'):
            self.assertNotIn(key, list(first.environment))
        self.assertNotIn('.hermes', first.environment['BH_HOME'])

    def test_console_ignores_a_foreign_python_path(self):
        foreign = self.root / 'foreign'
        foreign.mkdir()
        (foreign / 'psutil.py').write_text("raise RuntimeError('foreign dependency loaded')")
        environment = dict(os.environ, PYTHONPATH=str(foreign))
        result = subprocess.run([os.sys.executable, '-E', '-B', '-m', 'flow_browser'],
                                input="print('CLEAN_ENVIRONMENT')\nexit()\n", capture_output=True,
                                text=True, env=environment, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CLEAN_ENVIRONMENT', result.stdout)

    def test_display_name_change_is_refreshed_but_account_replacement_is_rejected(self):
        session = self.session()
        self.rows['Default']['name'] = 'Renamed'
        self.save()
        self.assertEqual(session._profile().name, 'Renamed')
        self.rows['Default']['user_name'] = 'other@example.invalid'
        self.save()
        with self.assertRaisesRegex(RuntimeError, 'removed or replaced'):
            session._profile()

    def test_cleanup_failure_retains_ownership_for_retry(self):
        provider = Mock(url='ws://fixture')
        provider.close.side_effect = [False, True]
        with patch('flow_browser.session.ChromeSession', return_value=provider), \
                patch('flow_browser.session.subprocess.run', return_value=Mock(returncode=0)):
            session = self.session().open()
            self.assertFalse(session.close())
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                session.open()
            self.assertTrue(session.close())

    def test_cleanup_reaps_only_the_daemon_bound_to_this_runtime_and_relay(self):
        provider = Mock(url='ws://fixture')
        provider.close.return_value = True
        with patch('flow_browser.session.ChromeSession', return_value=provider), \
                patch('flow_browser.session.subprocess.run', return_value=Mock(returncode=0)):
            session = self.session().open()
            owned = Mock(info={'cmdline': ['python', '-m', 'browser_harness.daemon']})
            peer = Mock(info=owned.info)
            owned.environ.return_value = dict(session.environment)
            peer.environ.return_value = dict(session.environment, BU_CDP_WS='ws://other')
            with patch('flow_browser.session.psutil.process_iter', return_value=[owned, peer]):
                self.assertTrue(session.close())
            owned.terminate.assert_called_once()
            owned.wait.assert_called_once_with(3)
            peer.terminate.assert_not_called()

    def test_runtime_cleanup_failure_remains_retryable(self):
        provider = Mock(url='ws://fixture')
        provider.close.return_value = True
        with patch('flow_browser.session.ChromeSession', return_value=provider), \
                patch('flow_browser.session.subprocess.run', return_value=Mock(returncode=0)):
            session = self.session().open()
            with patch('flow_browser.session.shutil.rmtree', side_effect=PermissionError):
                self.assertFalse(session.close())
            self.assertFalse(session.closed)
            self.assertTrue(session.runtime.exists())
            self.assertEqual(session.cleanup['runtime_error'], 'PermissionError')
            self.assertTrue(session.close())
            self.assertFalse(session.runtime.exists())

    def test_exit_cleanup_runs_before_the_runtime_directory_is_removed(self):
        marker = self.root / 'runtime-at-exit'
        code = '''
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from flow_browser import FlowSession
provider = Mock(url='ws://fixture')
provider.close.return_value = True
patch('flow_browser.session.ChromeSession', return_value=provider).start()
s = FlowSession(data=Path(sys.argv[1]))
s.open()
def stopped(*args, **kwargs):
    Path(sys.argv[2]).write_text(str(Path(s.environment['BH_RUNTIME_DIR']).exists()))
    return Mock(returncode=0)
patch('flow_browser.session.subprocess.run', side_effect=stopped).start()
'''
        subprocess.run([os.sys.executable, '-E', '-B', '-c', code, str(self.root), str(marker)],
                       capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(marker.read_text(), 'True')

    def test_close_interrupts_pending_execution_without_waiting_for_its_lock(self):
        provider = Mock(url='ws://fixture')
        provider.close.return_value = True
        entered, stopped = threading.Event(), threading.Event()
        process = Mock(returncode=1)
        process.poll.return_value = None
        process.terminate.side_effect = stopped.set
        def communicate(*args, **kwargs):
            entered.set()
            self.assertTrue(stopped.wait(2))
            return '', 'interrupted'
        process.communicate.side_effect = communicate
        with patch('flow_browser.session.ChromeSession', return_value=provider), \
                patch('flow_browser.session.subprocess.Popen', return_value=process), \
                patch('flow_browser.session.subprocess.run', return_value=Mock(returncode=0)):
            session = self.session()
            thread = threading.Thread(target=lambda: session.run('print(1)'))
            thread.start()
            self.assertTrue(entered.wait(2))
            self.assertTrue(session.close())
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def test_runtime_has_no_hermes_imports_or_private_flow_rpc(self):
        root = Path(__file__).parent / 'flow_browser'
        for path in root.rglob('*.py'):
            source = path.read_text()
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.ImportFrom) and not node.level and node.module:
                    self.assertNotIn(node.module.split('.')[0], {'hermes_cli', 'agent', 'tools', 'gateway'})
            self.assertNotIn('/data/batchexecute', source)

    def test_native_download_is_bound_to_the_owned_frame_and_completed_file(self):
        session = self.session()
        folder = self.root / 'downloads'
        folder.mkdir()
        destination = self.root / 'collected.bin'
        events = [[], [
            {'method': 'Page.downloadWillBegin', 'params': {'frameId': 'owned', 'guid': 'fixture', 'suggestedFilename': 'clip.bin'}},
            {'method': 'Page.downloadProgress', 'params': {'guid': 'fixture', 'state': 'completed', 'receivedBytes': 7}},
        ]]
        def cdp(method):
            if method == 'Page.getFrameTree':
                return {'frameTree': {'frame': {'id': 'owned'}}}
            self.assertEqual(method, 'Page.enable')
        def execute(code, **kwargs):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(code, {'cdp': cdp, 'drain_events': lambda: events.pop(0), 'wait': time.sleep})
            return subprocess.CompletedProcess([], 0, output.getvalue(), '')
        with patch.object(session, 'run', side_effect=execute):
            result = session.download("(folder / 'clip.bin').write_bytes(b'fixture')", destination, downloads=folder)
        self.assertEqual(result['bytes'], 7)
        self.assertEqual(destination.read_bytes(), b'fixture')

    def test_console_sigterm_runs_python_exit_cleanup(self):
        marker = self.root / 'exit-marker'
        process = subprocess.Popen([os.sys.executable, '-E', '-B', '-m', 'flow_browser'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            process.stdin.write("import atexit; from pathlib import Path; cleanup = atexit.register(lambda: Path(" + repr(str(marker)) + ").write_text('closed')); print('READY', flush=True)\n")
            process.stdin.flush()
            self.assertTrue(process.stdout.readline().strip().endswith('READY'))
            process.terminate()
            process.communicate(timeout=5)
            self.assertEqual(marker.read_text(), 'closed')
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


class InputTests(unittest.TestCase):
    def namespace(self, responses):
        namespace = {'fill_input': lambda *args: None, 'js': Mock(side_effect=responses),
                     'wait_for_element': Mock(), 'click_at_xy': Mock()}
        install(namespace)
        return namespace

    def test_click_waits_for_a_visible_unobstructed_target_then_clicks_once(self):
        namespace = self.namespace([None, [30, 50]])
        with patch('flow_browser.input_guard.time.sleep'):
            namespace['click_element']('#action')
        namespace['click_at_xy'].assert_called_once_with(30, 50)

    def test_unavailable_target_times_out_without_input(self):
        namespace = self.namespace([None])
        with self.assertRaisesRegex(RuntimeError, 'element not ready'):
            namespace['click_element']('#action', timeout=0)
        namespace['click_at_xy'].assert_not_called()

    def test_ambiguous_selector_stops_before_input(self):
        namespace = self.namespace([])
        namespace['js'].side_effect = RuntimeError('multiple visible elements')
        with self.assertRaisesRegex(RuntimeError, 'multiple visible elements'):
            namespace['click_element']('button')
        namespace['click_at_xy'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
