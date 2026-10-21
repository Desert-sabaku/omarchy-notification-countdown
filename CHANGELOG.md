# Changes

## 1.0.2

- Send notification JSON and image-copy metadata through stdin instead of process arguments.
- Centralize persistence in a private, atomic storage helper with 0700 directories and 0600 files.
- Repair existing history, image copies and legacy settings before reads/writes; refuse unsafe links.
- Keep bounded image copying, serialized jobs, history trimming, restore and DND behavior.
- Add permission migration, failure, payload round-trip and real Quickshell stdin/argv regression tests.

## 1.0.1

- Share one countdown per notification across all screens; hovering any copy pauses every view.
- Release hover registrations when a screen/delegate disappears or changes clocks.
- Identify the running implementation through a dedicated IPC response; stock pings and old versions no longer pass activation checks.
- Document the shell restart required after updating keepLoaded services.
- Add actual QML timer/lifecycle and model-wiring tests, plus helper activation regression tests.
