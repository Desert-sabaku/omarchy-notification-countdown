# Notification countdown

Adds a remaining-lifetime bar to notification popups and expires critical alerts after 15 seconds.

- Normal notifications retain upstream 8–30 second lifetimes; low-priority ones retain 5–30 seconds.
- Critical alerts expire after 15 seconds, including those whose sender requests persistence.
- The bar uses the same remaining fraction as the actual timer, with no seconds text.
- Hovering pauses both the timer and bar; a content update resets them.
- Right-click dismisses a notification. Upstream actions, DND and history are retained.
- The critical duration is currently a constant in Service.qml, not a settings UI.

## Install

This repository contains one Omarchy shell plugin with `manifest.json` at its root.
From a normal desktop terminal, after this repository has been published:

```sh
omarchy plugin add https://github.com/Desert-sabaku/omarchy-notification-countdown.git --enable
```

If already installed, update rather than adding a second copy:

```sh
omarchy plugin update dotfiles.notifications
omarchy restart shell
```

Both service manifests intentionally use `keepLoaded` to preserve timers and live state during unrelated
plugin reloads. Updating files or rescanning alone does **not** replace a running service instance.
Restart Omarchy shell from an unlocked desktop session after an update. Do not restart while the session is locked.
For dotfiles development, use the same restart step after editing linked plugin code.

The plugin ID is `dotfiles.notifications`. The existing ID is retained for compatibility with earlier dotfiles installations.
This is a clone of `omarchy.notifications`; `clonedFrom` metadata lets Omarchy replace the stock service and restore it later.
Do not enable another replacement of the same service alongside it.

## Development and existing dotfiles users

An existing dotfiles checkout already links these files. It must **not** run `plugin add` over the same ID.
Update its pinned submodule and use the dotfiles installer instead. The optional `scripts/enable-notification-timeout` helper
rescans plugins, backs up shell.json, and enables the plugin from a real desktop session; it attempts to
restore the stock service if its post-activation checks fail. No custom installer is required for new users.

## Disable / remove

```sh
omarchy plugin enable omarchy.notifications
omarchy plugin remove dotfiles.notifications
```

For a development checkout managed by dotfiles, switch to stock first and remove the corresponding managed
links through dotfiles instead of invoking `plugin remove` on a development checkout.

## Compatibility and validation

Based on installed Omarchy `4.0.6-1`. This fork uses shell internals; future compatibility is not guaranteed.
Requirements: Omarchy 4 / Quickshell, Python 3.9+ at runtime, and the usual Omarchy dependencies. Developer tests additionally require Node.js and the Qt QML test tools.

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests -v
# Real QML timer/lifecycle tests, also suitable for a headless session:
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= QT_STYLE_OVERRIDE=Fusion \
  QT_QUICK_CONTROLS_STYLE=Basic /usr/lib/qt6/bin/qmltestrunner -input tests/qml
```

Static validation and automated tests are available. A real desktop smoke test is still required before claiming
a verified release: confirm activation, normal operation, and restoration to the stock service.
No marketplace listing or approval is claimed. The GitHub repository must be created and pushed before
remote installation works.

## Upstream maintenance and license

Package updates are not merged automatically. Compare upstream changes against `upstream.json` before upgrading.
MIT; upstream copyright is retained in LICENSE. See THIRD_PARTY.md for attribution.

## Related work

[Omarchy issue #9361](https://github.com/omacom/omarchy/issues/9361) proposes bounded critical lifetimes and a decreasing
bar; no novelty is claimed. [byj-omarchy-notifications](https://github.com/BitYoungjae/byj-omarchy-notifications) is a
notification history/unread plugin alongside the stock daemon, rather than a popup countdown replacement.

## Privacy and existing storage

Notification JSON and image paths are sent to a Python storage helper through private stdin pipes, never as
process arguments or environment variables. Storage reads return through stdout pipes without logging payloads.
The helper sets a restrictive umask, enforces directories at 0700 and regular files at 0600, and atomically replaces
new files. On startup it repairs existing `~/.local/state/omarchy/notifications/` history/image files and the
legacy `~/.local/state/omarchy/notifications.json` settings file before the service reads or writes them.
The application state root itself is also made owner-only; unrelated state files inside it are not rewritten.
Unexpected symlinks, non-regular files or files owned by another account stop persistence rather than following
or modifying their targets. Popups may still be shown if persistence is disabled; storage failures are logged
without notification text. Images remain limited to 5 MiB with a bounded read; stdin jobs are limited to 16 MiB.

Updating files does not replace an already running keepLoaded service. After deploying version 1.0.2, restart
Omarchy shell from an unlocked desktop session. To repair existing permissions separately, from this checkout:

```sh
python3 scripts/notification-store.py repair "$HOME/.local/state/omarchy"
```

Owner-only modes protect against other local accounts. They do not encrypt stored notifications or protect
against root or other processes running under your own account.
