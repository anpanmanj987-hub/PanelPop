# Validation record

## 0.1.0a2 post-review checks on 2026-10-05

Observed in the fix session: Linux x86_64, Python 3.12.14, Pillow 12.3.0 (PanelPop/SnapPaste), qrcode 8.2, Node 24.19.0 (RoomPing), setuptools 84.0.0, build 1.6.1. **31 Python unittest cases passed, zero failures and zero skips.** Across all three projects: 120 tests.

- Fix: a successful SetCursorPos is no longer sufficient for input. GetCursorPos must report exactly the requested coordinates immediately before SendInput; mismatch/failure pauses and revokes permission without sending events.
- Fix: the absolute two-second frame deadline is checked after core safety inspection and inside both backends. The native check immediately precedes SendInput; equality is expired.
- Six added tests cover negative-coordinate success, clipped/read-failed cursor refusal, exact expiry, expiry during core checks and expiry during native checks. These are controlled user32 fixtures, not physical Windows results.

Wheel and sdist builds succeeded. Each distribution was installed separately into a newly created virtual environment without system site packages, from a working directory outside the checkout and with PYTHONPATH removed. Import location, version, module and console-script help/version, pip check, every bundled static route and authenticated loopback HTTP operations passed. PanelPop used only synthetic demo input; SnapPaste used only dry-run normalization; RoomPing checked QR, run start/end and exact 1,024-byte transfers. These checks do not verify native Windows or physical LAN/phone performance.

No Windows desktop is available in this environment. Physical Windows capture/input/clipboard, phones and LAN remain unverified. The local Playwright package has no installed browser executable, so the changed UI was not run in a real browser during this fix session. JSON/CSV native browser save/reopen remains unconfirmed; JSON generation/round-trip is tested in Node. GitHub CI and publication have not run. The original macOS evidence below is historical 0.1.0a1 evidence supplied with the source, not work performed in this fix session.

## Historical 0.1.0a1 record

Date: 2026-10-03. Host: macOS, Python 3.12, Pillow 12.3.0, qrcode 8.2. Native Windows and physical-phone validation have **not** been performed.

## Automated coverage

The controller's final full run on 2026-10-03 passed **25/25 unittest cases**, with no skips, including actual loopback HTTP sockets and all four CLI cases.

Independent repository command:

```sh
python -m unittest discover -s tests -v
```

Workspace implementation command (the shared development virtualenv is outside the standalone repo):

```sh
PYTHONPATH=panelpop/src .venv/bin/python -m unittest discover -s panelpop/tests -v
```

Coverage includes rectangle/count/bounds/NaN/bool/fraction rejection; negative monitor coordinates; view-only default; known/fresh frame use; expired/unknown frames; move/resize/PID/visibility/minimize pause; capture pre/post change; occlusion pause; Stop invalidation and explicit resume; correctly sized JPEG panels; separated authentication roles; Host/Origin/Fetch Metadata rejection; remote-admin rejection even with a token via controlled source-address policy; absent viewer stop/rearm routes; CSP/asset allowlist/no CORS; oversized/invalid JSON; Win32 client-origin/overlap/root/partial-input fixtures; CLI loopback defaults, explicit private-LAN requirement, invalid ports and help startup.

Win32 contract tests use a controlled fake `user32` fixture to check the backend's actual code and argument effects. They do not call Windows and do not validate the Windows ctypes ABI at runtime. The remote-admin test forces the TCP source-address policy to reject an actual loopback request; a physical remote host remains on the manual checklist.

## Browser synthetic demo

The controller verified the PC and viewer pages against a real local HTTP demo host in a macOS browser:

1. Open the local admin URL, load target list and synthetic live preview.
2. Drag a rectangle and apply it.
3. Enable control from the PC.
4. Open the separate viewer-token URL and see the cropped live panel.
5. Tap the panel and observe a yellow synthetic click marker.
6. Return to PC Stop; the viewer reports paused and removes panels.

This verifies JavaScript API requests, including Origin on mutations, UI selection and the displayed-frame tap pipeline. It does not verify a physical phone's viewport, network, QR scanner or native input.

## Distribution verification

The controller built wheel/sdist and verified source ZIP integrity and SHA-256. Both distributions were installed into separate temporary site directories outside the checkout; real HTTP HTML/JS/CSS and authenticated state responses passed. The wheel import path, version, all static assets and `python -m panelpop --help` passed. Existing validation-runtime dependencies were used; this is not a fresh Windows OS installation. CI is configured for Ubuntu and Windows with Python 3.10/3.12/3.14 but has not run on GitHub.

## Required interactive hardware checks before a wider release

- [ ] Windows 10 and Windows 11 native startup, failure message on unsupported DPI context, and client crop excluding window borders.
- [ ] 100%, 150%, 200% DPI; drag between monitors with different DPI; target at a negative virtual-screen origin.
- [ ] Single/multiple regions, portrait phone layout, correct edge clicks, full-window region, oversized target rejection.
- [ ] Move, resize, minimize, hide, close and reopen target. Pause must latch; restoring geometry must not automatically rearm.
- [ ] Overlapping higher window, transparent window, owned popup and taskbar; conservative capture refusal. Move an obstruction immediately before tapping.
- [ ] Native click to normal target; elevated target should report failure if UIPI blocks; partial event handling must not claim success.
- [ ] Tap and Stop concurrently. Stop's response must follow any serialized in-flight input, and future clicks must fail.
- [ ] Background/rotate/reconnect physical Android and iOS browsers; loss of Wi-Fi must remove or expire panels. Return must never allow an old image to be clicked.
- [ ] Physical LAN viewer cannot GET admin pages or APIs, configure, rearm or change mode, including with a deliberately supplied admin token.
- [ ] Scan the generated QR from a phone; verify secret-free request paths/logs and no external network requests.
- [ ] Fresh install from both wheel and sdist, CLI entry point and bundled static files; trusted-network firewall instructions.

Do not substitute fixture tests or Windows CI for these interactive hardware checks. Record Windows build, Python/Pillow version, monitor geometry/DPI, phone OS/browser, exact commands and results when they are completed.
