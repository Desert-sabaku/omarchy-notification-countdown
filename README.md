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
```

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
Requirements: Omarchy 4 / Quickshell and its usual dependencies. Developer tests additionally require Python 3 and Node.js.

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests -v
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
