import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ActivationTests(unittest.TestCase):
    def activate(self, response):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / 'bin'
            tools.mkdir()
            config = root / 'home/.config/omarchy/shell.json'
            config.parent.mkdir(parents=True)
            config.write_text('{}')
            marker = root / 'calls'
            (tools / 'omarchy-shell').write_text('''#!/bin/sh
if [ "$1" = notifications ]; then
  if [ "$2" = ping ]; then echo ok; else printf '%s\\n' "$RESPONSE"; fi
fi
''')
            (tools / 'omarchy').write_text('''#!/bin/sh
if [ "$2" = list ]; then echo '[{"id":"dotfiles.notifications"}]'; fi
if [ "$2" = enable ]; then printf '%s\\n' "$3" >> "$MARKER"; fi
''')
            (tools / 'sleep').write_text('#!/bin/sh\nexit 0\n')
            for tool in tools.iterdir():
                tool.chmod(0o755)
            env = os.environ.copy()
            env.update(HOME=str(root/'home'), PATH=str(tools)+':'+env['PATH'],
                       MARKER=str(marker), RESPONSE=response)
            script = Path(__file__).resolve().parents[1] / 'scripts/enable-notification-timeout'
            result = subprocess.run(['bash', str(script)], env=env, text=True, capture_output=True, timeout=15)
            return result, marker.read_text().splitlines()

    def test_exact_implementation_is_accepted(self):
        result, calls = self.activate(json.dumps(dict(pluginId='dotfiles.notifications', version='1.0.1',
                                                      criticalPopupDuration=15000, sharedCountdown=True)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['dotfiles.notifications'])

    def test_stock_ping_does_not_prove_activation(self):
        result, calls = self.activate('Function not found.')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ['dotfiles.notifications', 'omarchy.notifications'])

    def test_previous_implementation_is_rejected(self):
        result, calls = self.activate(json.dumps(dict(pluginId='dotfiles.notifications', version='1.0.0',
                                                      criticalPopupDuration=15000, sharedCountdown=True)))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, ['dotfiles.notifications', 'omarchy.notifications'])
