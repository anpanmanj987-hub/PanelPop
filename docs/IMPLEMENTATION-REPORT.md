# Implementation report

Date: 2026-10-03. Version: `0.1.0a1`. Scope: files only within the standalone `panelpop/` project. No git operations, remote project creation or external publishing were performed by this implementer.

## Delivered

- Independent src-layout package, MIT license, Python 3.10+ metadata, module/console CLI and explicit loopback/LAN/synthetic modes.
- Real Windows backend: PerMonitorV2 before UI, declared ctypes signatures and aligned INPUT structures, GetClientRect plus ClientToScreen origin, full pre/post capture identity/geometry verification, visible desktop ImageGrab with all_screens, conservative higher-window overlaps, WindowFromPoint root verification, checked SendInput count and partial-input release attempt.
- Shared-lock state machine: one to four bounded regions, monotonic two-second frame IDs, view-only default, local Stop/resume, geometry/PID/occlusion pause latching, stale/outside/non-finite input refusal.
- Authenticated bounded HTTP: distinct launch viewer/admin tokens, fragments/header credentials, loopback-only administration even with its token, exact Host/Origin, no CORS, fixed asset allowlist/CSP, QR, limits/timeouts and no request logging.
- Japanese PC setup/drag-selection/live preview UI, mobile-friendly live panels, visible demo label, connection/errors, expiry-aware tapping and PC-only Stop/control/rearm.
- Japanese and English day-one READMEs, CI, design, verification/hardware checklist, publishing and handoff documents.

## Test-first commands and observed results

1. Wrote core and real HTTP behavior tests before implementation. Ran:

   ```sh
   PYTHONPATH=panelpop/src .venv/bin/python -m unittest discover -s panelpop/tests -v
   ```

   RED: two module-import failures because `panelpop.core` and `panelpop.server` did not exist. This was a missing-module RED, not an observed assertion failure against a stub implementation.
2. Implemented core/demo, wrote Windows contract tests before its backend, and reran the same command. Ten core behavior tests passed; HTTP and Windows test imports failed because their modules were still absent.
3. Implemented backend, HTTP and bundled UI; reran the same command in the default sandbox. Four Windows contract tests and ten core tests passed; seven HTTP tests could not bind a loopback socket (`PermissionError: Operation not permitted`). This was an environment permission failure, not a product failure. The implementer's escalation wait was interrupted; the controller then performed the real HTTP suite through its already authorized validation harness.
4. Controller reported GREEN: all initial 21 tests passed, including actual HTTP sockets, without skips. Its workspace command was:

   ```sh
   PHONE_TOOLS_NODE=... .venv/bin/python tools/verify_all.py panelpop roomping
   ```

5. Added four CLI tests before `__main__.py` and ran:

   ```sh
   PYTHONPATH=panelpop/src .venv/bin/python -m unittest discover -s panelpop/tests -p test_cli.py -v
   ```

   RED: missing `panelpop.__main__` import. Implemented CLI, then reran: four tests passed (`Ran 4 tests ... OK`). Total project cases are now 25. The final full combined run belongs to the controller; the implementer did not repeat a permission-blocked HTTP bind.

The test-first workflow used missing-module REDs rather than individual failing assertions for every function. This record intentionally distinguishes them. Test expectations use fixed hand-derived coordinates/pixel sizes and observable behavior. Native API fixtures isolate the unavailable Windows boundary; real HTTP tests exercise the actual server and image responses.

## Browser verification supplied by controller

Against a real local HTTP synthetic host on macOS: admin window list → live preview → drag rectangle → apply → PC enable control → viewer live crop → tap with yellow synthetic marker → PC Stop → viewer paused with panels removed. No physical phone or Windows native operation was exercised.

## Remaining validation and limits

The controller is responsible for final 25-case combined tests, wheel/sdist build, clean install outside the checkout, packaged-asset smoke test and source archive. The project includes the packaging configuration, not a claim that this final build has already succeeded. Windows native capture/click/DPI/multiple monitors, elevated-target UIPI behavior, physical phone/LAN/QR and interactive race behavior remain unverified. See [VALIDATION.md](VALIDATION.md).

LAN HTTP is unencrypted. Win32 check/input is non-atomic and conservative occlusion rejection can refuse transparent or popup windows. Stop/input/capture are serialized; an in-flight OS operation can delay Stop and cannot be undone by it. No signed executable or public deployment is included.
