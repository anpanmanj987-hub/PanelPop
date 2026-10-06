# Changelog

## 0.1.0a3 — 2026-10-06

- Fix: on Windows 10/11, cloaked windows (suspended UWP apps, "Windows Input Experience" and other surfaces that DWM never draws) were treated as covering the target. They sit above normal windows, so most targets, including every maximized window, were refused as occluded. Cloaked windows are now ignored for occlusion and are not listed as targets; a failed cloak query still counts as covering.
- Fix: rejected POST requests on Windows could reach the browser as a connection reset instead of their error reply, because the socket was closed with the request body unread. The host now discards a bounded remainder of the body before closing.
- Verified on real Windows 11 hardware (150% scaling): capture, cropping, tap-to-click, and refusal after expiry, Stop and window movement. See [docs/VALIDATION.md](docs/VALIDATION.md).
- README rewritten with screenshots and a no-clone install; internal working notes removed from `docs/`.

## 0.1.0a2 — 2026-10-05

- A successful `SetCursorPos` is no longer enough to click: `GetCursorPos` must report exactly the requested coordinates right before `SendInput`. A mismatch or read failure pauses the session and revokes control without sending input.
- The two-second frame deadline is checked after the safety inspection and again inside the backend, immediately before `SendInput`; a frame at exactly its deadline is expired.

## 0.1.0a1 — 2026-10-03

- First alpha: one to four client-area regions, view-only default, PC-only Stop/resume/permission, loopback-only administration, two-second frames, synthetic `--demo` mode.
