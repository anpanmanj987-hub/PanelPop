import contextlib
import io
import subprocess
import sys
import unittest
from panelpop.__main__ import parse_args


class CLITests(unittest.TestCase):
    def test_default_is_loopback_and_port_8765(self):
        options = parse_args([])
        self.assertFalse(options.lan)
        self.assertEqual(options.port, 8765)
        self.assertIsNone(options.advertise)
        self.assertFalse(options.demo)
    def test_lan_requires_explicit_private_ipv4(self):
        for arguments in (['--lan'], ['--lan', '--advertise', '0.0.0.0'], ['--lan', '--advertise', 'example.com'], ['--lan', '--advertise', '8.8.8.8'], ['--advertise', '192.168.1.3']):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parse_args(arguments)
        self.assertEqual(parse_args(['--lan', '--advertise', '192.168.1.3']).advertise, '192.168.1.3')
    def test_invalid_ports_rejected(self):
        for port in ('0', '-1', '65536'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parse_args(['--port', port])
    def test_module_help_runs_without_windows_or_server(self):
        result = subprocess.run([sys.executable, '-m', 'panelpop', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--demo', result.stdout)
        self.assertIn('--lan', result.stdout)

if __name__ == '__main__': unittest.main()
