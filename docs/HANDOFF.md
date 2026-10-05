# Maintainer handoff

PanelPop is version `0.1.0a2` and independently installable from this tree. The parent workspace only provides development tooling; runtime code imports no sibling project.

## Main entry points

- `python -m panelpop --help` / console command `panelpop`: CLI, loopback default, explicit LAN/demo modes.
- `core.py`: region/geometry validation, two-second frame identity, shared capture/input/Stop lock, pause latching and PC resume.
- `windows.py`: pointer-safe Win32 signatures, PerMonitorV2 setup, client screen coordinates, visible desktop capture, conservative Z-order/root checks and checked SendInput count.
- `demo.py`: synthetic images and marker-only click feedback.
- `server.py`: 16 bounded handlers, role tokens, Host/Origin checks, loopback-only administration, fixed static allowlist and QR generation.
- `static/`: Japanese PC/phone UI, live preview rectangle editing, status/error feedback, local Stop and expiry-aware viewer.

## What is verified

The controller's final macOS run passed all 25 real-HTTP/core/native-contract/CLI tests and the browser demo flow. Wheel/sdist builds, separate-directory installations and installed real HTTP asset/API checks passed. See [VALIDATION.md](VALIDATION.md). Native Win32 APIs use test fixtures and still need interactive Windows verification. Physical smartphones/QR scanners/LAN hosts are not verified. The independent review found no important PanelPop defect.

## Known edges

Global OS input is not atomic with checks. The backend can conservatively reject transparent/cloaked windows and popups; target/admin overlap is refused, so the operator must arrange windows side by side. Elevated apps may reject SendInput via UIPI. Protected desktop pixels may be unavailable. Native OS capture can delay the shared lock and therefore a Stop acknowledgement; a returned Stop response means subsequent input is refused, not that an already issued OS event was undone.

The viewer and admin use separate session-storage tokens after removing the URL fragment. Reloading works in the same tab, but a new tab without the original token URL will have no credential. Only restart revokes launch tokens. Admin preview rectangle drafts are browser-local; reload shows zero draft rectangles even when a server configuration is active. Configuring/resuming explicitly resets control to view-only.

## Next work

Follow the hardware checklist in [VALIDATION.md](VALIDATION.md). Prioritize Windows ABI/capture/DPI and negative-monitor correctness before enhancing features. Preserve the input guard, immutable frame identity and single lock when adding behavior. Maintain the explicit distinction between synthetic fixture results and hardware evidence. Avoid enabling remote administration or adding public hosting to this private-network alpha without a separate design review.
