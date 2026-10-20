import QtQuick

// One instance per notification, shared by every screen that renders it.
Timer {
  id: root
  property real lifetime: 0
  property real remainingLifetime: 1
  property var hoveredScreens: ({})
  readonly property bool paused: Object.keys(hoveredScreens).length > 0
  signal expired()

  interval: 50
  repeat: true
  running: lifetime > 0 && remainingLifetime > 0 && !paused

  function setHovered(screenName, hovered) {
    var next = Object.assign({}, hoveredScreens)
    if (hovered) next[screenName] = true
    else delete next[screenName]
    hoveredScreens = next
  }

  function reset() { remainingLifetime = 1 }

  onTriggered: {
    remainingLifetime = Math.max(0, remainingLifetime - interval / lifetime)
    if (remainingLifetime <= 0) expired()
  }
}
