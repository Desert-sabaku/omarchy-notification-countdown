import QtQuick
import QtTest
import "../.." as Plugin

TestCase {
  name: "SharedPopupClock"
  when: windowShown

  Component { id: clockFactory; Plugin.PopupClock {} }
  Component { id: hoverFactory; Plugin.PopupHover {} }
  Component {
    id: viewFactory
    QtObject {
      property var clock: null
      readonly property real fraction: clock ? clock.remainingLifetime : 1
    }
  }

  function makeClock() {
    return createTemporaryObject(clockFactory, this, {lifetime: 400})
  }

  function test_anyScreenPausesAllViews() {
    var clock = makeClock()
    var a = createTemporaryObject(hoverFactory, this, {clock: clock, screenName: "A", hovered: true})
    var b = createTemporaryObject(hoverFactory, this, {clock: clock, screenName: "B", hovered: true})
    var viewA = createTemporaryObject(viewFactory, this, {clock: clock})
    var viewB = createTemporaryObject(viewFactory, this, {clock: clock})
    wait(500)
    compare(clock.remainingLifetime, 1)
    a.hovered = false
    wait(150)
    compare(clock.remainingLifetime, 1) // B is still hovered.
    b.hovered = false
    tryVerify(function() { return clock.remainingLifetime < 1 }, 1000)
    compare(viewA.fraction, viewB.fraction)
    tryCompare(clock, "remainingLifetime", 0, 2000)
    compare(viewA.fraction, 0)
    compare(viewB.fraction, 0)
  }

  function test_removedScreenReleasesPause() {
    var clock = makeClock()
    var hover = hoverFactory.createObject(this, {clock: clock, screenName: "removed", hovered: true})
    verify(clock.paused)
    hover.destroy()
    tryCompare(clock, "paused", false, 500)
    tryCompare(clock, "remainingLifetime", 0, 2000)
  }

  function test_clockReassignmentReleasesOldClock() {
    var first = makeClock()
    var second = makeClock()
    var hover = createTemporaryObject(hoverFactory, this, {clock: first, screenName: "A", hovered: true})
    verify(first.paused)
    hover.clock = second
    verify(!first.paused)
    verify(second.paused)
    hover.hovered = false
    verify(!second.paused)
  }

  function test_destroyedClockDoesNotLeaveHoverRegistration() {
    var first = clockFactory.createObject(this, {lifetime: 400})
    var second = makeClock()
    var hover = createTemporaryObject(hoverFactory, this, {clock: first, screenName: "A", hovered: true})
    first.destroy()
    wait(0)
    hover.clock = second
    verify(second.paused)
    hover.hovered = false
    verify(!second.paused)
  }

  function test_contentResetRestartsLifetime() {
    var clock = makeClock()
    tryVerify(function() { return clock.remainingLifetime < 1 }, 1000)
    clock.setHovered("A", true)
    clock.reset()
    compare(clock.remainingLifetime, 1)
    wait(500)
    compare(clock.remainingLifetime, 1)
    clock.setHovered("A", false)
    tryCompare(clock, "remainingLifetime", 0, 2000)
    clock.reset() // A reused timer must also restart after expiry.
    tryVerify(function() { return clock.remainingLifetime < 1 && clock.remainingLifetime > 0 }, 1000)
  }
}
