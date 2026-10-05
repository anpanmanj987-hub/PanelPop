# Panelpop 0.1.0a2 release notes

MIT-licensed alpha source release. See README and VALIDATION.md for operating assumptions and evidence.

- Fix: a successful SetCursorPos is no longer sufficient for input. GetCursorPos must report exactly the requested coordinates immediately before SendInput; mismatch/failure pauses and revokes permission without sending events.
- Fix: the absolute two-second frame deadline is checked after core safety inspection and inside both backends. The native check immediately precedes SendInput; equality is expired.
- Six added tests cover negative-coordinate success, clipped/read-failed cursor refusal, exact expiry, expiry during core checks and expiry during native checks. These are controlled user32 fixtures, not physical Windows results.

Physical Windows, phones and LAN remain unverified. Do not describe fixture tests, demo or dry-run as native hardware success. RoomPing native browser JSON/CSV saving remains unconfirmed. GitHub publication is a separate owner action.
