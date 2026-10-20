import QtQuick

// Release the exact registration even if a screen/delegate disappears or moves.
QtObject {
  id: root
  property var clock: null
  property string screenName: ""
  property bool hovered: false
  property var registeredClock: null
  property string registeredScreen: ""

  function release() {
    if (registeredClock) registeredClock.setHovered(registeredScreen, false)
    registeredClock = null
  }

  function sync() {
    if (registeredClock && (registeredClock !== clock || registeredScreen !== screenName || !hovered)) release()
    if (clock && hovered) {
      clock.setHovered(screenName, true)
      registeredClock = clock
      registeredScreen = screenName
    }
  }

  onClockChanged: sync()
  onScreenNameChanged: sync()
  onHoveredChanged: sync()
  Component.onDestruction: release()
}
