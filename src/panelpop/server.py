"""Bounded HTTP server with separate loopback-admin and viewer credentials."""
import hmac
import io
import ipaddress
import json
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
import qrcode
from .core import SafetyError
from .messages import language, text

STATIC = Path(__file__).with_name('static')
MAX_JSON = 32768
DRAIN_BYTES = 2 * MAX_JSON
DRAIN_SECONDS = 2.0
CSP ="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"


def is_loopback(address):
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 16
    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(*args, **kwargs)
    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise
    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def create_server(host, port, state, *, viewer_token=None, admin_token=None, advertised_host=None):
    server = BoundedHTTPServer((host, port), Handler)
    server.state = state
    server.viewer_token = viewer_token or secrets.token_urlsafe(32)
    server.admin_token = admin_token or secrets.token_urlsafe(32)
    if server.viewer_token == server.admin_token:
        server.server_close()
        raise ValueError('Admin and viewer tokens must differ')
    advertised = advertised_host or ('127.0.0.1' if host == '0.0.0.0' else host)
    server.allowed_hosts = {f'{name}:{server.server_port}' for name in ('127.0.0.1', 'localhost', advertised)}
    server.admin_address_allowed = is_loopback
    server.viewer_url = f'http://{advertised}:{server.server_port}/#token={server.viewer_token}'
    server.admin_url = f'http://127.0.0.1:{server.server_port}/admin#token={server.admin_token}'
    return server


class HTTPError(Exception):
    def __init__(self, status, key):
        self.status, self.key = status, key


class Handler(BaseHTTPRequestHandler):
    server_version = 'PanelPop/0.1'
    def setup(self):
        super().setup()
        self.connection.settimeout(3)
    def parse_request(self):
        ok = super().parse_request()
        length = self.headers.get('Content-Length', '') if ok else ''
        self.unread = int(length) if length.isascii() and length.isdecimal() else 0
        return ok
    def finish(self):
        # Rejections are sent before the body is read. Closing a socket with unread
        # data makes Windows reset the connection, and the browser then loses the
        # error response, so discard a bounded remainder after replying.
        try:
            if getattr(self, 'unread', 0) and not self.wfile.closed:
                self.wfile.flush()
                deadline, remaining = time.monotonic() + DRAIN_SECONDS, min(self.unread, DRAIN_BYTES)
                while remaining > 0 and time.monotonic() < deadline:
                    self.connection.settimeout(max(.01, deadline - time.monotonic()))
                    chunk = self.rfile.read1(remaining)
                    if not chunk:
                        break
                    remaining -= len(chunk)
        except OSError:
            pass
        finally:
            super().finish()
    def log_message(self, *args):
        # Request paths, headers and fragment-derived credentials never go to logs.
        pass
    def respond(self, status, body, content_type='application/json; charset=utf-8', extra=None):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def route(self, mutation=False):
        if len(self.path) > 2048:
            raise HTTPError(414, 'url_too_long')
        host = self.headers.get('Host', '')
        if host not in self.server.allowed_hosts or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise HTTPError(403, 'host_refused')
        if mutation and self.headers.get('Origin', '') != 'http://' + host:
            raise HTTPError(403, 'origin_mismatch')
        parts = urlsplit(self.path)
        if parts.scheme or parts.netloc:
            raise HTTPError(400, 'absolute_url')
        try:
            query = parse_qs(parts.query, max_num_fields=8)
        except ValueError:
            raise HTTPError(400, 'bad_query')
        path = parts.path
        admin = path == '/admin' or path.startswith('/api/admin/')
        if admin and not self.server.admin_address_allowed(self.client_address[0]):
            raise HTTPError(403, 'admin_loopback')
        if path.startswith('/api/'):
            token = self.headers.get('X-PanelPop-Token', '')
            expected = self.server.admin_token if admin else self.server.viewer_token
            if not hmac.compare_digest(token.encode(), expected.encode()):
                raise HTTPError(401, 'bad_token')
        return path, query
    def body(self):
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise HTTPError(415, 'json_required')
        length = self.headers.get('Content-Length', '')
        if not length.isascii() or not length.isdecimal():
            raise HTTPError(400, 'bad_length')
        length = int(length)
        if length > MAX_JSON:
            raise HTTPError(413, 'too_large')
        def invalid_constant(value):
            raise ValueError('Non-finite number')
        self.unread = 0
        try:
            body = json.loads(self.rfile.read(length), parse_constant=invalid_constant)
            if not isinstance(body, dict):
                raise ValueError('object required')
            return body
        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, 'bad_json')
    def execute(self, action):
        # The page sends its interface language; replies follow it (English otherwise).
        self.lang = language(self.headers.get('Accept-Language'))
        try:
            action()
        except HTTPError as error:
            self.respond(error.status, dict(error=text(error.key, self.lang)))
        except SafetyError as error:
            self.respond(409, dict(error=error.text(self.lang), status=self.server.state.status(self.lang)))
        except (KeyError, TypeError, ValueError, OverflowError):
            self.respond(400, dict(error=text('bad_input', self.lang)))
        except (TimeoutError, ConnectionError):
            self.close_connection = True
        except Exception:
            self.respond(500, dict(error=text('server_error', self.lang)))
    def do_GET(self):
        self.execute(self.get)
    def do_POST(self):
        self.execute(self.post)
    def do_OPTIONS(self):
        self.respond(405, dict(error=text('no_cors', language(self.headers.get('Accept-Language')))))
    def get(self):
        path, query = self.route()
        state = self.server.state
        allowlist = {'/': ('viewer.html', 'text/html; charset=utf-8'), '/admin': ('admin.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/text.js': ('text.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path in allowlist:
            name, kind = allowlist[path]
            return self.respond(200, (STATIC / name).read_bytes(), kind)
        if path == '/api/state':
            frame, error = None, ''
            status = state.status(self.lang)
            if status['configured'] and not status['paused']:
                try:
                    frame = state.capture()
                except SafetyError as failure:
                    error = failure.text(self.lang)
            return self.respond(200, dict(status=state.status(self.lang), frame=frame, error=error))
        if path == '/api/frame':
            return self.respond(200, state.image(query['id'][0], int(query['panel'][0])), 'image/jpeg')
        if path == '/api/admin/windows':
            with state.lock:
                windows = state.backend.windows()
            return self.respond(200, dict(windows=windows, status=state.status(self.lang)))
        if path == '/api/admin/status':
            return self.respond(200, dict(status=state.status(self.lang)))
        if path == '/api/admin/preview':
            geometry, jpeg = state.preview(int(query['hwnd'][0]))
            return self.respond(200, jpeg, 'image/jpeg', {'X-Image-Width': str(geometry.width), 'X-Image-Height': str(geometry.height)})
        if path == '/api/admin/connect':
            return self.respond(200, dict(url=self.server.viewer_url, demo=bool(state.backend.demo)))
        if path == '/api/admin/qr':
            buffer = io.BytesIO()
            qrcode.make(self.server.viewer_url).save(buffer, format='PNG')
            return self.respond(200, buffer.getvalue(), 'image/png')
        raise HTTPError(404, 'not_found')
    def post(self):
        path, _ = self.route(mutation=True)
        routes = {'/api/click', '/api/admin/configure', '/api/admin/mode', '/api/admin/stop', '/api/admin/resume'}
        if path not in routes:
            raise HTTPError(404, 'no_action')
        body, state = self.body(), self.server.state
        if path == '/api/click':
            state.click(body['id'], body['panel'], body['x'], body['y'])
        elif path == '/api/admin/configure':
            state.configure(body['hwnd'], body['regions'])
        elif path == '/api/admin/mode':
            state.set_control(body['control'])
        elif path == '/api/admin/stop':
            state.stop()
        elif path == '/api/admin/resume':
            state.resume()
        self.respond(200, dict(ok=True, status=state.status(self.lang)))
