# PanelPop design

The host has four boundaries: `core.py` owns frame/input safety state, `windows.py` owns Win32/visible-desktop capture, `server.py` owns authenticated HTTP, and bundled `static/` owns PC/phone UI. `demo.py` is explicitly synthetic. The CLI configures the backend before opening any UI. There are no imports from sibling projects or external runtime services.

## State and input

One `RLock` protects target identity and geometry, regions, retained frames, control permission, pause, capture and OS input. Initial mode is view-only. Explicit PC configuration clears old frames and restores view-only. Stop latches pause and clears frames. A changed or unsafe target also latches pause. Resume is a PC-only mutation: it verifies the same HWND/PID, validates current regions and occlusion, clears frames and returns to view-only. There is no phone stop/rearm endpoint.

The immutable geometry snapshot stores HWND, PID, client screen origin, width, height, visibility and minimized state. Capture verifies the full snapshot before and after `ImageGrab.grab`. A changed snapshot invalidates the entire session. Regions are bounded integer rectangles; normalized tap coordinates must be finite numbers in `[0,1)`. Pixel coordinates use `floor(normalized * region_size) + region_origin + client_screen_origin`, preserving negative monitor coordinates.

Frames use random opaque IDs, a monotonic timestamp, the verified geometry/regions, and JPEGs. The server retains at most eight frames and accepts each for at most two seconds. Frame image requests also recheck target safety. Stop and reconfiguration invalidate IDs immediately. The viewer associates one identity with a complete set of images, swaps after all responses arrive, refuses local expiry, and clears panels on errors/expiry. Browser deadlines begin before the frame request, conservatively accounting for transfer latency.

The absolute frame deadline is passed to both native and demo input backends together with the state's monotonic clock. Equality with the deadline is expired. Core checks it after target inspection; the native backend checks before movement and immediately before `SendInput`, after all native inspections and cursor readback. An expiry before entering the backend rejects the tap; native input failures latch pause and revoke permission.

## Windows boundary

`SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` runs before window enumeration, capture or opening the browser. If awareness cannot be enabled, startup fails unless the existing awareness is already per-monitor. The origin is `ClientToScreen(hwnd, POINT(0,0))`, and dimensions come from `GetClientRect`. Capturing the screen bounding box with Pillow's `all_screens=True` avoids mixing non-client borders with client coordinates. Win32 functions have explicit `argtypes` and `restype`; handles and `ULONG_PTR` remain pointer-sized. `INPUT` includes the full mouse/keyboard/hardware union and its native alignment.

`IsWindowVisible` is never treated as proof of unobstructed pixels. The backend walks higher top-level windows in Z order and conservatively rejects any visible, non-minimized overlapping rectangle. Before input, `WindowFromPoint` plus `GetAncestor(GA_ROOT)` must resolve to the target. Geometry, overlaps and root are checked again before/after moving the cursor, then two global `SendInput` events send left down/up. The return count must be two; on a partial result an up-only release is attempted, failure is reported, and the core pauses.

After those checks, pointer-bound `GetCursorPos(LPPOINT) -> BOOL` must succeed and report exactly the requested physical screen coordinates. This detects successful `SetCursorPos` calls clamped by `ClipCursor`, as well as cursor movement during inspection. Mismatch/read failure sends no input and pauses. PanelPop never changes another application's clipping rectangle. Cursor readback, deadline inspection and global input still cannot form an atomic desktop transaction.

Checks and OS operations are not atomic. A window can move, close or become covered between the final check and global input. Global cursor movement affects the user's desktop. UIPI can block injection into elevated apps; `SendInput` does not reliably identify UIPI as its cause. Conservative overlap rejection may reject transparent/cloaked/popup windows. Protected pixels and native capture hangs remain OS limitations. Locking prevents internal Stop/mode races, not desktop races.

## HTTP boundary

Loopback is the default listener; LAN bind requires `--lan --advertise RFC1918_IPV4`. Each launch generates independent `secrets.token_urlsafe(32)` admin and viewer tokens. URLs carry tokens only in fragments. JavaScript stores the appropriate role token in tab session storage, removes the fragment from the visible URL, and passes credentials in `X-PanelPop-Token`. Admin requires an actual loopback TCP source address even if the token is correct. Forwarded headers are ignored.

Host must match an exact configured authority. Mutations require `Origin == "http://" + Host`. Cross-site Fetch Metadata is refused when present. There is no CORS allow header. Fetch retains its default CORS mode so same-origin mutations still send Origin under `Referrer-Policy: no-referrer`. Assets come from a four-route fixed allowlist with a self-only CSP; there are no CDN scripts, fonts or remote images.

The HTTP server uses 16 handler slots, a three-second connection timeout, 32 KiB JSON bodies, bounded query/URL lengths and non-finite JSON rejection. Geometry bounds limit capture allocation. It uses short-lived HTTP/1.0 responses, no caches and no request logging. This is a private-network alpha, not an internet production service or TLS gateway.
