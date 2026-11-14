"""Exercise independent sessions against local pages in the original Chrome."""
import concurrent.futures
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flow_browser import FlowSession


class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<title>Flow session fixture</title><input id=field><button id=action '
                         b'onclick="document.querySelector(\'#result\').textContent=\'clicked\'">Run</button>'
                         b'<p id=result></p>')

    def log_message(self, *args):
        pass


def verify(profile='Default'):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    manual = FlowSession(profile)
    agents = [FlowSession(profile) for _ in range(4)]
    report = {}
    try:
        manual.navigate(url)
        manual.evaluate("window.manualMarker='KEEP'")
        def prepare(pair):
            index, session = pair
            session.navigate(url)
            result = session.run(f"fill_input('#field', 'agent-{index}')\n"
                                 "click_element('#action')")
            assert result.returncode == 0, result.stderr
            assert session.evaluate("document.querySelector('#result').textContent") == 'clicked'
            assert len(session.provider.owned) == 1, session.provider.owned
            return session.provider.wire.call('Browser.getWindowForTarget', {
                'targetId': next(iter(session.provider.owned))})['windowId']
        with concurrent.futures.ThreadPoolExecutor() as pool:
            windows = list(pool.map(prepare, enumerate(agents)))
        assert len(set(windows)) == 4, windows
        report['four_distinct_agent_windows'] = True
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            slow = pool.submit(agents[0].evaluate, 'new Promise(r=>setTimeout(()=>r(true),4000))')
            time.sleep(.3)
            assert agents[1].evaluate("document.querySelector('#field').value") == 'agent-1'
            assert time.monotonic() - started < 3.5
            assert slow.result() is True
        report['independent_parallel_commands'] = True
        for session in agents:
            session.screenshot()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pending = pool.submit(agents[0].evaluate, 'new Promise(r=>setTimeout(()=>r(true),15000))')
            time.sleep(.5)
            started = time.monotonic()
            assert agents[0].close()
            try:
                pending.result(timeout=5)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Interrupted execution unexpectedly completed')
            assert time.monotonic() - started < 8
        report['close_interrupts_in_flight_command'] = True
        assert agents[1].evaluate("document.querySelector('#field').value") == 'agent-1'
        assert manual.evaluate('window.manualMarker') == 'KEEP'
        report['peer_and_independent_manual_fixture_preserved'] = True
    finally:
        cleanup = [session.close() for session in [*agents, manual]]
        server.shutdown()
        assert all(cleanup), cleanup
    report['all_test_session_cleanup_confirmed'] = True
    return report


if __name__ == '__main__':
    print(json.dumps(verify(sys.argv[1] if len(sys.argv) > 1 else 'Default'), indent=2))
