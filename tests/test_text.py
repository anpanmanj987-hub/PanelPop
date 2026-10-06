import http.client
import json
import re
import threading
import unittest
from pathlib import Path

from panelpop.core import PanelState, SafetyError
from panelpop.demo import DemoBackend
from panelpop.messages import MESSAGES, language, text
from panelpop.server import create_server

STATIC = Path(__file__).resolve().parents[1] / 'src' / 'panelpop' / 'static'
SOURCE = Path(__file__).resolve().parents[1] / 'src' / 'panelpop'


def interface_text():
    script = (STATIC / 'text.js').read_text(encoding='utf-8')
    return json.loads(script[script.index('{'):script.rindex('}') + 1])


class InterfaceTextTests(unittest.TestCase):
    def test_both_languages_have_the_same_keys(self):
        table = interface_text()
        self.assertEqual(set(table), {'ja', 'en'})
        self.assertEqual(set(table['ja']), set(table['en']))
        for lang in table:
            for key, value in table[lang].items():
                with self.subTest(lang=lang, key=key):
                    self.assertTrue(value.strip())

    def test_every_key_used_by_the_pages_exists(self):
        keys = set(interface_text()['en'])
        used = set()
        for page in ('admin.html', 'viewer.html'):
            html = (STATIC / page).read_text(encoding='utf-8')
            used |= set(re.findall(r'data-i18n="([^"]+)"', html))
            for pairs in re.findall(r'data-i18n-attr="([^"]+)"', html):
                used |= {pair.split(':')[1] for pair in pairs.split(';')}
        used |= set(re.findall(r"\bt\('([a-z_]+)'", (STATIC / 'app.js').read_text(encoding='utf-8')))
        self.assertTrue(used)
        self.assertEqual(used - keys, set())

    def test_no_untranslated_japanese_left_in_app_js(self):
        self.assertIsNone(re.search('[぀-ヿ一-鿿]', (STATIC / 'app.js').read_text(encoding='utf-8')))


class ServerTextTests(unittest.TestCase):
    def test_every_message_has_both_languages(self):
        for key, (ja, en) in MESSAGES.items():
            with self.subTest(key=key):
                self.assertRegex(ja, '[぀-ヿ一-鿿]')
                self.assertNotRegex(en, '[぀-ヿ一-鿿]')

    def test_every_raised_key_exists(self):
        raised = set()
        for path in SOURCE.glob('*.py'):
            source = path.read_text(encoding='utf-8')
            raised |= set(re.findall(r"(?:SafetyError|_pause|text)\(\s*'([a-z_]+)'", source))
            raised |= set(re.findall(r"HTTPError\(\d+, '([a-z_]+)'\)", source))
        self.assertTrue(raised)
        self.assertEqual(raised - set(MESSAGES), set())

    def test_language_follows_the_first_ja_or_en_tag(self):
        for header, expected in (('ja', 'ja'), ('ja-JP,en;q=0.8', 'ja'), ('en-US,ja;q=0.5', 'en'),
                                 ('fr-FR,ja;q=0.7', 'ja'), ('de-DE', 'en'), ('', 'en'), (None, 'en')):
            with self.subTest(header=header):
                self.assertEqual(language(header), expected)

    def test_errors_default_to_english_and_keep_details(self):
        error = SafetyError('input_failed', 'access denied')
        self.assertEqual(str(error), 'Input failed: access denied')
        self.assertEqual(error.text('ja'), '入力に失敗しました：access denied')
        self.assertEqual(text('stopped', 'xx'), MESSAGES['stopped'][1])


class LocalizedHTTPTests(unittest.TestCase):
    def setUp(self):
        self.state = PanelState(DemoBackend())
        self.server = create_server('127.0.0.1', 0, self.state, viewer_token='view-secret', admin_token='admin-secret')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, token='view-secret', language=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        headers = {'Host': f'127.0.0.1:{self.server.server_port}', 'X-PanelPop-Token': token}
        if language:
            headers['Accept-Language'] = language
        connection.request('GET', path, headers=headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_replies_follow_accept_language(self):
        self.assertEqual(self.get('/api/state', token='wrong', language='ja')[1]['error'], MESSAGES['bad_token'][0])
        self.assertEqual(self.get('/api/state', token='wrong', language='en-US')[1]['error'], MESSAGES['bad_token'][1])
        self.assertEqual(self.get('/api/state', token='wrong')[1]['error'], MESSAGES['bad_token'][1])

    def test_pause_reason_is_localized_per_request(self):
        self.state.configure(1, [[0, 0, 10, 10]])
        self.state.stop()
        self.assertEqual(self.get('/api/state', language='ja')[1]['status']['reason'], MESSAGES['stopped'][0])
        self.assertEqual(self.get('/api/state', language='en')[1]['status']['reason'], MESSAGES['stopped'][1])

    def test_text_script_is_served(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        connection.request('GET', '/text.js', headers={'Host': f'127.0.0.1:{self.server.server_port}'})
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b'PANELPOP_TEXT', response.read())
        connection.close()


if __name__ == '__main__':
    unittest.main()
