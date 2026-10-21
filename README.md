# Notification Countdown for Omarchy

Adds a remaining-lifetime progress bar to notification popups and expires critical alerts after 15 seconds.

## Features

- **Standard Notification Lifetimes**: Normal notifications retain upstream 8–30 second lifetimes; low-priority notifications retain 5–30 seconds.
- **Critical Alert Expiration**: Critical alerts expire after 15 seconds, including those whose sender requests persistence.
- **Visual Progress Bar**: The bar uses the same remaining fraction as the actual timer, with no text displaying remaining seconds.
- **Interactive Controls**:
  - Hovering pauses both the timer and the progress bar.
  - Content updates reset the timer and bar.
  - Right-click dismisses a notification.
  - Upstream actions, Do Not Disturb (DND), and history are fully retained.
- **Configuration Note**: The critical notification duration is currently a constant defined in `Service.qml` (no settings UI yet).

## Installation

This repository contains an Omarchy shell plugin with `manifest.json` at its root.

To install the plugin from a normal desktop terminal:

```sh
omarchy plugin add [https://github.com/Desert-sabaku/omarchy-notification-countdown.git](https://github.com/Desert-sabaku/omarchy-notification-countdown.git) --enable

```

If already installed, update the plugin instead of adding it again:

```sh
omarchy plugin update dotfiles.notifications
omarchy restart shell
```

> [!IMPORTANT]
> Both service manifests intentionally use `keepLoaded` to preserve timers and live state during unrelated plugin reloads. Updating files or rescanning alone does **not** replace a running service instance.
> **Restart Omarchy shell from an unlocked desktop session** after an update. Do not restart while the session is locked.

### Plugin ID & Compatibility

* Plugin ID: `dotfiles.notifications` (retained for compatibility with earlier dotfiles installations).
* This plugin is a clone of `omarchy.notifications`. The `clonedFrom` metadata allows Omarchy to replace the stock service and restore it later.
* **Do not enable another replacement of the same service alongside it.**

## Development and Existing Dotfiles Users

An existing dotfiles checkout already links these files. It must **not** run `plugin add` over the same ID. Instead, update its pinned submodule and use the dotfiles installer.

The optional `scripts/enable-notification-timeout` helper:

* Rescans plugins,
* Backs up `shell.json`, and
* Enables the plugin from a real desktop session (it attempts to restore the stock service if post-activation checks fail).

No custom installer is required for new users.

## Disable / Removal

To switch back to the stock notification service and remove the plugin:

```sh
omarchy plugin enable omarchy.notifications
omarchy plugin remove dotfiles.notifications
```


> [!NOTE]
> For development checkouts managed by dotfiles. Switch to the stock service first, then remove the corresponding managed links through dotfiles instead of invoking `plugin remove`.

## Compatibility and Validation

Tested and based on Omarchy `4.0.6-1`. Because this fork interacts with shell internals, future compatibility is not guaranteed.

### Requirements

* **Runtime**: Omarchy 4 / Quickshell, Python 3.9+, standard Omarchy dependencies.
* **Development/Testing**: Node.js, Qt QML test tools (`qmltestrunner`).

### Running Tests

```sh
# Static validation and Python unit tests
omarchy plugin validate .
python3 -m unittest discover -s tests -v

# Real QML timer/lifecycle tests (headless-compatible)
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= QT_STYLE_OVERRIDE=Fusion \
  QT_QUICK_CONTROLS_STYLE=Basic /usr/lib/qt6/bin/qmltestrunner -input tests/qml
```

> **Release Verification**:
> Static validation and automated tests are provided, but a real desktop smoke test (verifying activation, normal operation, and stock service restoration) is required before declaring a verified release.

## Upstream Maintenance & License

* Package updates are not merged automatically. Compare upstream changes against `upstream.json` before upgrading.
* **License**: MIT (Upstream copyright is retained in `LICENSE`). See `THIRD_PARTY.md` for attribution.

## Related Work

* [Omarchy issue #9361](https://www.google.com/search?q=https://github.com/omacom/omarchy/issues/9361): Proposes bounded critical lifetimes and a decreasing bar (no novelty is claimed).
* [byj-omarchy-notifications](https://www.google.com/search?q=https://github.com/BitYoungjae/byj-omarchy-notifications): A notification history/unread plugin running alongside the stock daemon, rather than a popup countdown replacement.

## Privacy & Security

Notification JSON data and image paths are passed to a Python storage helper via private `stdin` pipes—never as process arguments or environment variables. Storage reads return via `stdout` pipes without logging payloads.

### File Permissions & Hardening

* **Access Controls**: The helper sets a restrictive umask, enforcing directory permissions at `0700` and regular file permissions at `0600` with atomic file replacement.
* **Startup Repair**: Repairs existing `~/.local/state/omarchy/notifications/` history/image files and the legacy `~/.local/state/omarchy/notifications.json` settings file before reading/writing.
* **Safety Checks**: The application state root itself is restricted to owner-only access. Unexpected symlinks, non-regular files, or files owned by another account stop persistence rather than following or modifying targets.
* **Fail-safe Operation**: Popups will still function if persistence fails or is disabled (failures are logged without notification text).
* **Limits**: Images are limited to 5 MiB with bounded reads; `stdin` jobs are capped at 16 MiB.

### Repairing Existing Permissions Manually

After deploying version `1.0.2`, restart the Omarchy shell from an unlocked desktop session. To repair existing file permissions separately:

```sh
python3 scripts/notification-store.py repair "$HOME/.local/state/omarchy"
```

> [!NOTE]
> Owner-only permissions protect against other local accounts. They do not encrypt stored notifications or protect against root/processes running under your own user account.*
