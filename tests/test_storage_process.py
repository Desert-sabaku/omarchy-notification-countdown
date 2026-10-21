import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shutil.which('qs')


@unittest.skipUnless(RUNNER, 'Quickshell is required')
class StorageProcessTests(unittest.TestCase):
    def test_real_quickshell_process_passes_large_payload_only_through_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state, audit = root/'state', root/'argv-audit'
            wrapper = root/'helper.py'
            wrapper.write_text('''import pathlib, runpy, sys
with pathlib.Path(%r).open('ab') as output:
    output.write(pathlib.Path('/proc/self/cmdline').read_bytes()+b'\\n')
sys.argv[0] = %r
runpy.run_path(sys.argv[0], run_name='__main__')
''' % (str(audit), str(ROOT/'scripts/notification-store.py')))
            test = root/'shell.qml'
            test.write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "%s" as Plugin
ShellRoot {
  id: test
  property int completed: 0
  Plugin.StorageJob {
    id: job
    helperPath: %s
    stateDirectory: %s
    action: "popup"
    stdout: StdioCollector { id: output; waitForEnd: true }
    onExited: function(code) {
      if (code !== 0) { console.log("STORAGE_TEST_FAIL"); Qt.quit(); return }
      test.completed++
      if (test.completed === 1) {
        action = "history"
        payload = {name: "200-2.json", json: test.message(), copies: [], limit: 10}
        running = true
      } else if (test.completed === 2) {
        action = "read-history"
        payload = {}
        running = true
      } else {
        if (output.text.indexOf("PRIVATE_ARGV_FIXTURE") < 0) {
          console.log("STORAGE_TEST_FAIL"); Qt.quit(); return
        }
        console.log("STORAGE_TEST_PASS")
        Qt.quit()
      }
    }
  }
  function message() {
    return JSON.stringify({summary: "PRIVATE_ARGV_FIXTURE", body: "payload".repeat(20000)})
  }
  Component.onCompleted: {
    job.payload = {name: "100-1.json", json: message(), copies: []}
    job.running = true
  }
  Timer { interval: 15000; running: true; onTriggered: { console.log("STORAGE_TEST_TIMEOUT"); Qt.quit() } }
}
''' % (ROOT.as_uri(), json.dumps(str(wrapper)), json.dumps(str(state))))
            env = os.environ.copy()
            for key in ['WAYLAND_DISPLAY', 'DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE']:
                env.pop(key, None)
            runtime = root/'runtime'
            runtime.mkdir(mode=0o700)
            env.update(QT_QPA_PLATFORM='offscreen', QT_QPA_PLATFORMTHEME='',
                       QT_STYLE_OVERRIDE='Fusion', QT_QUICK_CONTROLS_STYLE='Basic',
                       HOME=str(root/'home'), XDG_RUNTIME_DIR=str(runtime),
                       XDG_CONFIG_HOME=str(root/'config'), XDG_CACHE_HOME=str(root/'cache'),
                       DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent')
            result = subprocess.run([RUNNER, '--no-color', '-p', str(test)], env=env,
                                    text=True, capture_output=True, timeout=25)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('STORAGE_TEST_PASS', result.stdout+result.stderr)
            self.assertNotIn('STORAGE_TEST_FAIL', result.stdout+result.stderr)
            self.assertNotIn(b'PRIVATE_ARGV_FIXTURE', audit.read_bytes())
            for path in [state/'notifications/100-1.json', state/'notifications/history/200-2.json']:
                data=json.loads(path.read_text())
                self.assertEqual(data['summary'], 'PRIVATE_ARGV_FIXTURE')
                self.assertEqual(data['body'], 'payload'*20000)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
