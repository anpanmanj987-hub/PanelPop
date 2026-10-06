# Validation record

This page separates what has been observed on real hardware from what is only covered by automated tests with fixtures.

## Real Windows check — 2026-10-06 (0.1.0a3)

Environment: Windows 11 (build 26200), one 1920×1200 display at 150% scaling, Python 3.14.8, Pillow 12.3.0.

Target: a small DPI-unaware WinForms window that counts clicks on a button (so Windows scales it, which exercises the PerMonitorV2 path). PanelPop ran as the real `WindowsBackend` behind the real HTTP server, driven over loopback HTTP with the admin and viewer tokens.

| Step | Result |
|---|---|
| Admin window list | Target listed; cloaked windows not listed |
| Preview | 720×450 client area (480×300 logical at 150%), title bar and borders excluded |
| Configure two regions, capture | Both JPEG panels match the client-area crops |
| Tap while view-only | 409, no click |
| Allow control, tap panel 2 | 200, target counted exactly one click; next capture shows it |
| Tap on a frame older than 2 s | 409, no click |
| Tap after PC Stop | 409, no click |
| Move the target window, tap | 409, session paused and control revoked, no click |

The cursor was restored to its original position afterwards.

Two findings from this session were fixed in 0.1.0a3:

- **Cloaked windows.** On this machine 11 of 21 visible top-level windows were cloaked, including a 1×1 window at the top of the Z order at (0,0) and a full-screen "Windows Input Experience" surface. The previous occlusion check counted them, so any maximized target was refused as covered.
- **Connection reset on rejected POSTs.** Rejecting a request before reading its body and then closing the socket made Windows send a reset, so clients intermittently saw a network error instead of the 4xx reply. Reproduced by the HTTP tests on Windows and fixed by draining a bounded remainder of the body.

An earlier attempt that placed the DPI-unaware test window partly off-screen was refused with "cursor position does not match": Windows clamped the cursor to the screen edge and PanelPop declined to click, as designed.

## English interface — 2026-10-06 (0.1.0a4)

Headless Edge 154 against the synthetic demo host: the settings page and the phone viewer were exercised in English and Japanese (select a window, drag two regions, apply, allow control, tap). In English no Japanese text remained apart from the language toggle; no script errors. Clicking the toggle switched the page in place, and a reload without `?lang` kept the choice.

## Automated tests

```sh
python -m unittest discover -s tests -v
```

44 cases: rectangle and coordinate validation, negative monitor origins, view-only default, frame expiry (including exactly at the deadline and expiry during native checks), geometry/PID/visibility/minimize pause latching, occlusion and cloaked-window handling, Stop and explicit resume, cursor readback mismatch, partial `SendInput`, HTTP roles, Host/Origin/Fetch-Metadata checks, loopback-only administration, CSP and static allowlist, body limits, reset-free rejections, CLI defaults, and the language layer (matching Japanese/English keys, every used key defined, replies and pause reasons localized per request).

Win32 contract tests use a fake `user32`/`dwmapi`; they check the backend's logic, not the Windows ABI. GitHub Actions runs the suite on Ubuntu and Windows with Python 3.10, 3.12 and 3.14 and builds the wheel and sdist.

## Not yet verified

- [ ] A physical Android or iOS phone over a real LAN: QR scan, rotation, backgrounding, Wi-Fi loss (panels must disappear and old images must never be clickable).
- [ ] A LAN client trying admin pages or APIs, including with a correct admin token (must be refused by source address).
- [ ] Windows 10.
- [ ] Multiple monitors, mixed DPI, and a target at a negative virtual-screen origin.
- [ ] Elevated (administrator) target apps: UIPI must produce a reported failure, never a claimed success.
- [ ] Transparent overlays, owned pop-ups and the taskbar overlapping the target.
- [ ] Tap and Stop at the same moment.

When you check one of these, please record the Windows build, display layout and scaling, Python and Pillow versions, phone OS and browser, and the exact result.
