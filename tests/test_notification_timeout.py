from pathlib import Path
import re
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node.js is required')
class NotificationTimeoutTests(unittest.TestCase):
    def test_actual_duration_policy(self):
        service = (Path(__file__).resolve().parents[1] /
                   'Service.qml').read_text()
        script = 'const NotificationUrgency = {Critical: 2, Low: 0};\n'
        for name, value in re.findall(r'readonly property int (\w*PopupDuration): (\d+)', service):
            script += f'const {name} = {value};\n'
        start = service.index('  function durationFor(')
        end = service.index('  // DND bypass', start)
        script += service[start:end]
        script += '''
const assert = require('node:assert/strict');
// Critical alerts expire even if the sender requests persistent/long popups.
for (const requested of [0, -1, 1000, 60000]) {
  assert.equal(durationFor(2, requested), 15000);
}
assert.equal(durationFor(1, 0), 8000);
assert.equal(durationFor(1, 12000), 12000);
assert.equal(durationFor(1, 60000), 30000);
assert.equal(durationFor(0, 0), 5000);
assert.equal(durationFor(0, 60000), 30000);
'''
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
