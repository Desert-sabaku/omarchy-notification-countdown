# Changes

## 1.0.1

- Share one countdown per notification across all screens; hovering any copy pauses every view.
- Release hover registrations when a screen/delegate disappears or changes clocks.
- Identify the running implementation through a dedicated IPC response; stock pings and old versions no longer pass activation checks.
- Document the shell restart required after updating keepLoaded services.
- Add actual QML timer/lifecycle and model-wiring tests, plus helper activation regression tests.
