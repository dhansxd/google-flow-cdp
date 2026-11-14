"""One owned Chrome window and one Browser Harness daemon per Flow session."""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path

import psutil

from ._chrome.relay import ChromeSession
from .input_guard import prepare_code
from .profiles import CHROME_DATA, resolve_profile


OBSERVE = r"""(() => {
  const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const label = e => e.getAttribute('aria-label') || e.getAttribute('title') || e.innerText || e.textContent || '';
  return {
    url: location.href, title: document.title, ready: document.readyState,
    text: document.body?.innerText || '',
    controls: Array.from(document.querySelectorAll('button,input,textarea,select,a[href],[role=button],[role=link],[role=radio],[role=option],[role=tab],[role=checkbox],[role=switch],[role=slider],[role=combobox],[role^=menuitem],[contenteditable=true]'))
      .filter(visible).map(e => ({tag: e.tagName.toLowerCase(), role: e.getAttribute('role'),
        name: label(e).trim(), placeholder: e.getAttribute('placeholder'), type: e.getAttribute('type'),
        value: e.value ?? null, disabled: !!e.disabled, pressed: e.getAttribute('aria-pressed'),
        checked: e.getAttribute('aria-checked') ?? e.checked ?? null,
        selected: e.getAttribute('aria-selected'), expanded: e.getAttribute('aria-expanded'),
        href: e.getAttribute('href'), id: e.id || null})),
    images: Array.from(document.images).filter(visible).map(e => ({alt:e.alt,src:e.currentSrc,ready:e.complete && e.naturalWidth>0})),
    videos: Array.from(document.querySelectorAll('video')).filter(visible).map(e => ({src:e.currentSrc,ready:e.readyState,duration:Number.isFinite(e.duration)?e.duration:null}))
  };
})()"""


class FlowSession:
    def __init__(self, profile='Default', *, directory=None, data=CHROME_DATA, python=None):
        self.data = Path(data)
        self.profile = resolve_profile(profile, self.data)
        if self.profile is None:
            raise ValueError('Choose an existing profile from list_profiles().')
        self.id = uuid.uuid4().hex
        self.directory = Path(directory or Path(__file__).resolve().parents[1] / 'state/browser-sessions' / self.id)
        self.python = str(python or sys.executable)
        self.provider = None
        self.runtime = None
        self.environment = None
        self.lock = threading.RLock()
        self.command_lock = threading.Lock()
        self.process = None
        self.cleanup = None
        self.closing = False
        self.closed = False
        atexit.register(self.close)

    def _profile(self):
        current = resolve_profile(self.profile.id, self.data)
        if (current is None or current.identity != self.profile.identity
                or (current.account or '').casefold() != (self.profile.account or '').casefold()):
            raise RuntimeError('The selected Chrome profile was removed or replaced. Select from the current inventory.')
        self.profile = current
        return current

    def open(self):
        with self.lock:
            if self.closed or self.closing:
                raise RuntimeError('This Flow session is closed.')
            self._profile()
            if self.provider is not None:
                return self
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.runtime = Path(tempfile.mkdtemp(prefix='flow-h-', dir='/tmp'))
            self.provider = ChromeSession(self.data, self.profile.id)
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(('BU_', 'BH_', 'BROWSER_USE_', 'BROWSER_HARNESS_'))
                           and key not in {'PYTHONPATH', 'PYTHONHOME', '__PYVENV_LAUNCHER__'}}
            # The relay exposes only this session's seed page. The default namespace
            # reuses it, while the unique IPC directory isolates the daemon.
            environment.update(BU_NAME='default', BU_CDP_WS=self.provider.url,
                               BH_RUNTIME_DIR=str(self.runtime), BH_HOME=str(self.directory / 'harness'),
                               BH_TMP_DIR=str(self.directory / 'screenshots'),
                               BH_AGENT_WORKSPACE=str(self.directory / 'workspace'), BH_TELEMETRY='0', BH_RECORD='0')
            self.environment = environment
            return self

    def run(self, code, *, timeout=120):
        with self.command_lock:
            with self.lock:
                self.open()
                process = self.process = subprocess.Popen(
                    [self.python, '-E', '-m', 'browser_harness.run'], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.environment)
            try:
                output, error = process.communicate(prepare_code(code), timeout=timeout)
                return subprocess.CompletedProcess(process.args, process.returncode, output, error)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise
            except BaseException:
                if process.poll() is None:
                    process.kill()
                process.communicate()
                raise
            finally:
                with self.lock:
                    if self.process is process:
                        self.process = None

    def evaluate(self, expression, *, timeout=120):
        return self._read('js(' + repr(expression) + ')', timeout=timeout)

    def accessibility(self):
        return self._read("cdp('Accessibility.getFullAXTree')['nodes']")

    def _read(self, expression, *, timeout=120):
        code = 'import json\nprint("FLOW_RESULT=" + json.dumps(' + expression + ', ensure_ascii=False))'
        result = self.run(code, timeout=timeout)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        values = [line.removeprefix('FLOW_RESULT=') for line in result.stdout.splitlines()
                  if line.startswith('FLOW_RESULT=')]
        if len(values) != 1:
            raise RuntimeError('Browser observation did not return one result.')
        return json.loads(values[0])

    def navigate(self, url):
        if self.evaluate('location.href') != url:
            result = self.run('goto_url(' + repr(url) + ")\nwait_for_element('body', timeout=30)")
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)
        return self.observe()

    def observe(self):
        return self.evaluate(OBSERVE)

    def screenshot(self):
        return self.run('print(capture_screenshot())')

    def download(self, action, destination, *, timeout=180, downloads=None):
        """Click once and collect the completed file bound to this page's download."""
        destination = Path(destination).resolve()
        if downloads is None:
            preferences = self.data / self.profile.id / 'Preferences'
            settings = json.loads(preferences.read_text()) if preferences.exists() else {}
            downloads = settings.get('download', {}).get('default_directory', str(Path.home() / 'Downloads'))
        code = rf'''import hashlib, json, re, shutil, tempfile, time
from pathlib import Path
folder = Path({str(downloads)!r}).expanduser()
destination = Path({str(destination)!r})
destination.parent.mkdir(parents=True, exist_ok=True)
before = {{p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in folder.glob('*') if p.is_file()}}
def frame_ids(node):
    return {{node['frame']['id']}}.union(*(frame_ids(child) for child in node.get('childFrames', [])))
frames = frame_ids(cdp('Page.getFrameTree')['frameTree'])
cdp('Page.enable')
drain_events()
exec({action!r}, globals())
started, completed = {{}}, {{}}
deadline = time.monotonic() + {float(timeout)!r}
receipt = None
while time.monotonic() < deadline:
    for event in drain_events():
        params = event.get('params', {{}})
        if event.get('method') == 'Page.downloadWillBegin' and params.get('frameId') in frames:
            started[params['guid']] = params
        if event.get('method') == 'Page.downloadProgress' and params.get('state') == 'completed':
            completed[params['guid']] = params
    if len(started) > 1:
        raise RuntimeError('More than one download began from this action. Inspect the completed downloads.')
    for guid, download in started.items():
        if guid not in completed:
            continue
        name = Path(download['suggestedFilename']).name
        stem, suffix = Path(name).stem, Path(name).suffix
        total = completed[guid].get('receivedBytes') or completed[guid].get('totalBytes')
        candidates = []
        for path in folder.glob('*'):
            if not path.is_file() or not (path.name == name or re.fullmatch(re.escape(stem) + r' \(\d+\)' + re.escape(suffix), path.name)):
                continue
            info = path.stat()
            if (info.st_size, info.st_mtime_ns) != before.get(path.name) and info.st_size == total:
                candidates.append(path)
        if len(candidates) > 1:
            raise RuntimeError('Completed download file is ambiguous.')
        if not candidates:
            continue
        source = candidates[0]
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
        try:
            shutil.copyfile(source, temporary)
            digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
            if digest != hashlib.sha256(source.read_bytes()).hexdigest():
                raise RuntimeError('Downloaded file changed during collection.')
            temporary.replace(destination)
            receipt = {{'path': str(destination), 'bytes': destination.stat().st_size, 'sha256': digest}}
        finally:
            temporary.unlink(missing_ok=True)
        break
    if receipt:
        break
    wait(.2)
if receipt is None:
    raise RuntimeError('Download was clicked once. Inspect its original outcome before another click.')
print('FLOW_DOWNLOAD=' + json.dumps(receipt))
'''
        result = self.run(code, timeout=timeout + 15)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        receipts = [json.loads(line.removeprefix('FLOW_DOWNLOAD=')) for line in result.stdout.splitlines()
                    if line.startswith('FLOW_DOWNLOAD=')]
        if len(receipts) != 1 or receipts[0]['path'] != str(destination):
            raise RuntimeError('Download completion was not returned.')
        return receipts[0]

    def close(self):
        with self.lock:
            if self.closed:
                return True
            self.closing = True
            process = self.process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
        targets_closed = self.provider is None or self.provider.close()
        daemon_closed = True
        daemon_error = None
        if self.environment is not None:
            try:
                result = subprocess.run([self.python, '-E', '-m', 'browser_harness.run', '--reload'],
                                        capture_output=True, text=True, env=self.environment, timeout=15)
                daemon_closed = result.returncode == 0
                if not daemon_closed:
                    daemon_error = result.stderr or result.stdout
            except (OSError, subprocess.TimeoutExpired) as error:
                daemon_closed = False
                daemon_error = type(error).__name__
            try:
                for daemon in psutil.process_iter(['cmdline']):
                    try:
                        if (daemon.info['cmdline'] or [])[-2:] != ['-m', 'browser_harness.daemon']:
                            continue
                        environment = daemon.environ()
                        if (environment.get('BH_RUNTIME_DIR') != str(self.runtime)
                                or environment.get('BU_CDP_WS') != self.provider.url):
                            continue
                        daemon.terminate()
                        try:
                            daemon.wait(3)
                        except psutil.TimeoutExpired:
                            daemon.kill()
                            daemon.wait(3)
                    except psutil.NoSuchProcess:
                        continue
            except psutil.Error as error:
                daemon_closed = False
                daemon_error = type(error).__name__
        with self.lock:
            self.cleanup = {'targets_closed': targets_closed, 'daemon_closed': daemon_closed,
                            'daemon_error': daemon_error}
            if daemon_closed and targets_closed:
                if self.runtime is not None:
                    try:
                        shutil.rmtree(self.runtime)
                    except FileNotFoundError:
                        pass
                    except OSError as error:
                        self.cleanup['runtime_error'] = type(error).__name__
                        return False
                self.closed = True
                atexit.unregister(self.close)
            return self.closed

    def __enter__(self):
        return self.open()

    def __exit__(self, *args):
        if not self.close():
            raise RuntimeError('Flow session cleanup is still pending.')
