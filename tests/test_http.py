import http.client
import json
import threading
import unittest

from panelpop.core import PanelState
from panelpop.demo import DemoBackend
from panelpop.server import create_server, is_loopback


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.state = PanelState(DemoBackend())
        self.server = create_server('127.0.0.1', 0, self.state, viewer_token='view-secret', admin_token='admin-secret')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = '127.0.0.1:' + str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
    def request(self, path, method='GET', payload=None, token='view-secret', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        h = {'Host': self.host, 'X-PanelPop-Token': token}
        if method == 'POST':
            h['Origin'] = 'http://' + self.host
            h['Content-Type'] = 'application/json'
        h.update(headers or {})
        connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=h)
        response = connection.getresponse()
        body = response.read()
        result = (response.status, dict(response.getheaders()), body)
        connection.close()
        return result
    def test_authentication_required_and_roles_separate(self):
        self.assertEqual(self.request('/api/state', token='')[0], 401)
        self.assertEqual(self.request('/api/admin/windows')[0], 401)
        self.assertEqual(self.request('/api/state', token='admin-secret')[0], 401)
        self.assertEqual(self.request('/api/admin/windows', token='admin-secret')[0], 200)
    def test_host_origin_and_fetch_site_rejected(self):
        self.assertEqual(self.request('/api/state', headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.request('/api/click', 'POST', {}, headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('/api/click', 'POST', {}, headers={'Origin': ''})[0], 403)
        self.assertEqual(self.request('/api/state', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
    def test_remote_address_cannot_admin_even_with_token(self):
        self.assertTrue(is_loopback('127.0.0.1'))
        self.assertTrue(is_loopback('::1'))
        self.assertFalse(is_loopback('192.168.1.4'))
        self.server.admin_address_allowed = lambda address: False
        self.assertEqual(self.request('/api/admin/windows', token='admin-secret')[0], 403)
        self.assertEqual(self.request('/admin')[0], 403)
    def test_real_http_config_frame_and_view_only_click(self):
        status, _, body = self.request('/api/admin/configure', 'POST', {'hwnd': 1, 'regions': [[10, 20, 100, 80]]}, 'admin-secret')
        self.assertEqual(status, 200, body)
        status, _, body = self.request('/api/state')
        self.assertEqual(status, 200, body)
        frame = json.loads(body)['frame']
        status, headers, body = self.request('/api/frame?id=' + frame['id'] + '&panel=0')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'image/jpeg')
        self.assertTrue(body.startswith(b'\xff\xd8'))
        self.assertEqual(self.request('/api/click', 'POST', {'id': frame['id'], 'panel': 0, 'x': .5, 'y': .5})[0], 409)
        self.assertEqual(self.request('/api/admin/mode', 'POST', {'control': True}, 'admin-secret')[0], 200)
        self.assertEqual(self.request('/api/click', 'POST', {'id': frame['id'], 'panel': 0, 'x': .5, 'y': .5})[0], 200)
    def test_rejected_post_body_does_not_reset_the_reply(self):
        # Windows resets a socket closed with unread data, hiding the error from the browser.
        for _ in range(10):
            self.assertEqual(self.request('/api/click', 'POST', {'pad': 'x' * 30000}, token='stale')[0], 401)
    def test_phone_stop_and_resume_routes_do_not_exist(self):
        for path in ('/api/stop', '/api/resume', '/api/mode'):
            self.assertEqual(self.request(path, 'POST', {})[0], 404)
    def test_static_allowlist_csp_and_no_cors(self):
        status, headers, body = self.request('/')
        self.assertEqual(status, 200)
        self.assertIn(b'PanelPop', body)
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(self.request('/../server.py')[0], 404)
    def test_invalid_json_overlarge_and_nonfinite_input(self):
        self.assertEqual(self.request('/api/admin/configure', 'POST', {'hwnd': 1, 'regions': [[0, 0, float('nan'), 2]]}, 'admin-secret')[0], 400)
        self.assertEqual(self.request('/api/click', 'POST', {}, headers={'Content-Length': '999999'})[0], 413)

if __name__ == '__main__':
    unittest.main()
