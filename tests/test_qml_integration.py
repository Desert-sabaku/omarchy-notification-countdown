from pathlib import Path
import os
import subprocess
import tempfile
import unittest

RUNNER = Path('/usr/lib/qt6/bin/qmltestrunner')
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(RUNNER.exists(), 'Qt QML test tools are required')
class QmlIntegrationTests(unittest.TestCase):
    def test_production_clock_model_wiring(self):
        source = (ROOT / 'Service.qml').read_text()
        start = source.index('  Instantiator {')
        begin = source.index('{', start)
        depth, end = 1, begin + 1
        while depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        clocks = source[start:end].replace('delegate: PopupClock {', 'delegate: Plugin.PopupClock {')
        test = '''import QtQuick
import QtTest
import "%s" as Plugin
TestCase {
  id: service
  name: "ProductionClockModel"
  when: windowShown
  property int clockRevision: 0
  ListModel { id: popupModel }
  function durationFor(urgency, timeout) { return timeout }
  function expirePopup(index) { popupModel.remove(index) }
%s
  function init() { popupModel.clear() }
  function cleanup() { popupModel.clear(); wait(0) }
  function add(summary, timeout) {
    popupModel.append({urgency: 1, expireTimeout: timeout, summary: summary, body: "", image: ""})
  }
  function test_expiryAfterModelIndexChange() {
    add("first", 150)
    add("second", 1500)
    var second = popupClocks.objectAt(1)
    verify(second !== null)
    tryCompare(popupModel, "count", 1, 1000)
    compare(popupModel.get(0).summary, "second")
    compare(popupClocks.objectAt(0), second)
    tryCompare(popupModel, "count", 0, 2500)
  }
  function test_modelContentUpdateResetsSharedClock() {
    add("original", 400)
    var clock = popupClocks.objectAt(0)
    tryVerify(function() { return clock.remainingLifetime < 1 }, 1000)
    clock.setHovered("A", true)
    popupModel.setProperty(0, "summary", "updated")
    compare(clock.remainingLifetime, 1)
    wait(500)
    compare(popupModel.count, 1)
    compare(clock.remainingLifetime, 1)
    clock.setHovered("A", false)
    tryCompare(popupModel, "count", 0, 1500)
  }
}
''' % (ROOT.as_uri(), clocks)
        with tempfile.TemporaryDirectory() as directory:
            testfile = Path(directory) / 'tst_model.qml'
            testfile.write_text(test)
            env = os.environ.copy()
            env.update(QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='',
                       QT_STYLE_OVERRIDE='Fusion', QT_QUICK_CONTROLS_STYLE='Basic')
            result = subprocess.run([str(RUNNER), '-input', str(testfile)], env=env,
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("QWARN", result.stdout + result.stderr)
