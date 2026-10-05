"""Standalone command line launcher; Windows-free synthetic demo is explicit."""
import argparse
import ipaddress
import sys
import webbrowser
from . import __version__
from .core import PanelState, SafetyError


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='PanelPop: Windows client-area panels for your phone (alpha).')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--demo', action='store_true', help='Synthetic panels only; no screen capture or OS input')
    parser.add_argument('--port', type=int, default=8765, help='HTTP port (default: 8765)')
    parser.add_argument('--lan', action='store_true', help='Explicitly listen on LAN as well as loopback')
    parser.add_argument('--advertise', metavar='PRIVATE_IPV4', help='PC LAN IPv4 address used in phone URL/QR; requires --lan')
    parser.add_argument('--open', action='store_true', help='Open loopback-only PC admin UI in your default browser')
    options = parser.parse_args(argv)
    if not 1 <= options.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    if options.lan != bool(options.advertise):
        parser.error('--lan and --advertise PRIVATE_IPV4 must be provided together')
    if options.advertise:
        try:
            address = ipaddress.IPv4Address(options.advertise)
            ranges = (ipaddress.IPv4Network('10.0.0.0/8'), ipaddress.IPv4Network('172.16.0.0/12'), ipaddress.IPv4Network('192.168.0.0/16'))
            if not any(address in network for network in ranges):
                raise ValueError('RFC1918 address required')
            options.advertise = str(address)
        except ValueError:
            parser.error('--advertise must be an RFC1918 private IPv4 address of this PC')
    return options


def main(argv=None):
    options = parse_args(argv)
    server = None
    try:
        if options.demo:
            from .demo import DemoBackend
            backend = DemoBackend()
        else:
            from .windows import WindowsBackend
            # This enables PerMonitorV2 before any capture or UI is opened.
            backend = WindowsBackend()
        from .server import create_server
        state = PanelState(backend)
        server = create_server('0.0.0.0' if options.lan else '127.0.0.1', options.port, state,
                               advertised_host=options.advertise or '127.0.0.1')
        print(f'PanelPop {__version__}' + (' — SYNTHETIC DEMO: no desktop capture / no OS input' if options.demo else ' — Windows visible-desktop mode'), flush=True)
        print('PC admin (local only, keep secret): ' + server.admin_url, flush=True)
        print('Viewer URL (keep secret): ' + server.viewer_url, flush=True)
        print('LAN HTTP is unencrypted. Use a trusted private network only.' if options.lan else 'Loopback only. For a phone, restart with --lan --advertise PC_PRIVATE_IPV4.', flush=True)
        print('Stop/rearm from the PC admin UI; Ctrl+C closes the host.', flush=True)
        if options.open:
            webbrowser.open(server.admin_url)
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        if server is not None:
            server.state.stop()
        print('\nPanelPop stopped.', flush=True)
    except (OSError, SafetyError) as error:
        print('PanelPop: ' + str(error), file=sys.stderr)
        return 2
    finally:
        if server is not None:
            server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
