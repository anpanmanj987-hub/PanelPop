# PanelPop

PanelPop shares one to four live regions of a Windows application's client area with a phone browser. It starts in view-only mode. The PC operator can explicitly allow a phone tap to become a left mouse click.

**Version 0.1.0a2 · MIT · Windows 10/11 · Python 3.10+.** This repository is independent and includes no signed executable. A clearly marked synthetic demo runs on macOS/Linux without desktop capture or OS input. [日本語README](README.md)

Version 0.1.0a2 rechecks frame expiry after safety inspection and immediately before native input. A failed cursor readback or actual position differing from the requested screen coordinates prevents input, pauses the session and revokes control permission.

Version 0.1.0a2 is the post-review source release. [Validation](docs/VALIDATION.md) separates the current Linux checks from historical 0.1.0a1 macOS evidence.

## Install and start

From this repository's root on Windows:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\python -m panelpop --open
```

The default listener is `127.0.0.1:8765`. Open the **PC admin** URL printed in the terminal on this PC. `--open` opens that local settings page in your default browser.

For a phone, explicitly enable LAN access and advertise this PC's private IPv4 address. Replace the example address with your own:

```powershell
.venv\Scripts\python -m panelpop --lan --advertise 192.168.1.20 --open
```

Use the same trusted private network on the PC and phone. If Windows Firewall prompts, allow TCP 8765 only on the appropriate private network. Wi-Fi client isolation, VPNs and different subnets can prevent access. Only RFC1918 IPv4 addresses are accepted. IPv6 and reverse-proxy hosting are outside this alpha's scope.

## Use

1. Select a window in the PC settings page and load its live preview. Arrange the window and settings browser side by side so they do not overlap.
2. Drag one to four rectangles in the preview, then apply the regions. Coordinates are integer pixels within the client area.
3. Open the viewer URL or scan its QR code from the phone. Panels update in view-only mode.
4. If needed, enable phone control on the PC. Taps on a panel become left clicks at that location.
5. Use the PC's persistent **Stop** button to stop both display and input. Rearm on the PC; this restores view-only mode. `Ctrl+C` shuts down the host.

Changes to the target position, size, process identity, visibility or minimized state, and detected occlusion, latch a pause. Moving the window back does not resume it automatically. Clear the obstruction and explicitly resume on the PC, or select/configure the target again. A reused window handle with another PID requires selection again. The rectangle counter is the current draft selection; zero after reloading the admin page does not clear previously applied regions.

## Synthetic demo

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m panelpop --demo --open
```

The synthetic demo uses generated moving panels. An allowed tap draws a yellow marker; it never captures the desktop or sends OS input. To use the demo from a phone, also provide `--lan --advertise YOUR_PC_PRIVATE_IPV4`.

## Limits and precautions

- LAN HTTP is unencrypted. Use only a trusted private network; do not expose it to the internet. Each launch creates separate random viewer/admin credentials. URLs and QR codes contain secrets. Restart the host to revoke them.
- Admin APIs require both the admin token and a loopback TCP source address. A phone cannot stop, rearm, configure or change control mode. Viewer credentials cannot call admin APIs. No request URLs or credentials are logged.
- Every displayed frame expires after two seconds. Unknown/expired frames and invalid/outside tap coordinates are refused. Network failure clears the display and does not report input success.
- Capture reads visible desktop pixels, cropped to the client area. Higher overlapping windows are conservatively rejected, including transparent windows and popups. Protected video may not capture correctly.
- Per-monitor DPI awareness and negative monitor coordinates are supported in code. Checks and OS input are not atomic: a last-moment change can still misdirect input. Do not use this alpha for safety-critical operations.
- Input moves the PC cursor and sends left down/up. Windows UIPI can block input to elevated apps. A failed or partial `SendInput` is reported and pauses the session. There is no keyboard, scroll, long-press or multi-touch support.
- Bounds: 16 million target pixels, 8192 pixels per edge, four regions, eight retained frames, 16 concurrent handlers, 32 KiB JSON bodies, three-second socket timeout. Stop shares the capture/input lock and can wait for a pending native OS operation.

## Development and verification

```sh
python -m pip install -e . build
python -m unittest discover -s tests -v
python -m panelpop --help
python -m build
```

On 2026-10-03, macOS verification passed 21 core/native-contract/real-HTTP tests and four CLI tests. A browser against the real HTTP synthetic demo completed target selection, preview rectangle dragging, apply, PC control enable, phone-style panel tap and PC Stop. **Native Windows capture/input/DPI/multiple monitors and a physical smartphone are unverified.** Linux/Windows CI runs tests and builds wheel/sdist across Python versions; its native API fixtures are not interactive Windows validation.

See [design](docs/DESIGN.md), [validation and hardware checklist](docs/VALIDATION.md), [publishing](docs/PUBLISHING.md), [handoff](docs/HANDOFF.md) and [implementation report](docs/IMPLEMENTATION-REPORT.md).
