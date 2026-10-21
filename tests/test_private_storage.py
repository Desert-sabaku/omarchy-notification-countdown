import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'scripts/notification-store.py'


class PrivateStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.state = self.base / 'omarchy'
        self.popup = self.state / 'notifications'
        self.history = self.popup / 'history'
        self.images = self.popup / 'images'

    def run_job(self, action, job=None, success=True):
        command = [sys.executable, str(HELPER), action, str(self.state)]
        result = subprocess.run(command, input=json.dumps(job or {})+'\n', text=True,
                                capture_output=True, timeout=10,
                                preexec_fn=lambda: os.umask(0o022))
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr)
        return result

    def modes_are_private(self):
        for parent, dirs, files in os.walk(self.state):
            self.assertEqual(stat.S_IMODE(Path(parent).stat().st_mode), 0o700)
            for name in files:
                self.assertEqual(stat.S_IMODE((Path(parent)/name).stat().st_mode), 0o600)

    def test_legacy_history_images_and_settings_are_repaired_without_data_loss(self):
        self.history.mkdir(parents=True)
        self.images.mkdir()
        fixtures = [self.popup/'1-1.json', self.history/'2-2.json', self.images/'2-2-image',
                    self.state/'notifications.json']
        for file in fixtures:
            file.write_text('PRIVATE_FIXTURE')
            file.chmod(0o644)
        for directory in [self.state, self.popup, self.history, self.images]:
            directory.chmod(0o755)
        self.run_job('repair')
        self.modes_are_private()
        for file in fixtures:
            self.assertEqual(file.read_text(), 'PRIVATE_FIXTURE')

    def test_popup_and_dnd_history_use_private_files_and_round_trip_text(self):
        source = self.base/'source.png'
        source.write_bytes(b'IMAGE_FIXTURE')
        secret = 'PRIVATE_FIXTURE: 日本語 "quotes" `backticks`\nsecond line'
        entry = dict(summary=secret, body=secret)
        job = dict(name='100-1.json', json=json.dumps(entry), copies=[
            {'from':str(source), 'to':str(self.images/'100-1-image')}])
        self.run_job('popup', job)
        result = self.run_job('read-popup')
        self.assertEqual(json.loads(result.stdout), entry)
        self.assertEqual((self.images/'100-1-image').read_bytes(), b'IMAGE_FIXTURE')
        self.run_job('archive',dict(name='100-1.json',limit=10))
        self.assertFalse((self.popup/'100-1.json').exists())
        self.assertEqual(json.loads(self.run_job('read-history').stdout),entry)
        self.run_job('history',dict(name='200-2.json',json=json.dumps(entry),copies=[],limit=1))
        self.assertFalse((self.history/'100-1.json').exists())
        self.assertFalse((self.images/'100-1-image').exists())
        self.run_job('settings',dict(dnd=True,summary=secret))
        self.assertEqual(json.loads((self.state/'notifications.json').read_text()),{'version':3,'dnd':True})
        self.modes_are_private()
        self.run_job('clear')
        self.assertEqual(list(self.history.iterdir()),[])

    def test_symlink_repair_is_rejected_without_touching_external_target(self):
        self.run_job('repair')
        outside=self.base/'outside'
        outside.write_text('PRIVATE_FIXTURE')
        outside.chmod(0o640)
        (self.images/'link').symlink_to(outside)
        result=self.run_job('repair',success=False)
        self.assertEqual(stat.S_IMODE(outside.stat().st_mode),0o640)
        self.assertNotIn('PRIVATE_FIXTURE',result.stderr)
        self.assertNotIn(str(outside),result.stderr)

    def test_symlinked_state_root_is_rejected(self):
        outside=self.base/'outside'
        outside.mkdir(mode=0o755)
        self.state.symlink_to(outside)
        self.run_job('repair',success=False)
        self.assertEqual(stat.S_IMODE(outside.stat().st_mode),0o755)
        self.assertEqual(list(outside.iterdir()),[])

    def test_traversal_is_rejected_and_payload_never_logged(self):
        secret='PRIVATE_FIXTURE'
        result=self.run_job('popup',dict(name='../escape',json=secret,copies=[]),success=False)
        self.assertFalse((self.state/'escape').exists())
        self.assertNotIn(secret,result.stdout+result.stderr)
        result=subprocess.run([sys.executable,str(HELPER),'popup',str(self.state)],
                              input=secret, text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,1)
        self.assertNotIn(secret,result.stdout+result.stderr)

    def test_fifo_and_oversized_image_do_not_block_or_create_copies(self):
        self.run_job('repair')
        fifo=self.base/'fifo'
        os.mkfifo(fifo)
        large=self.base/'large'
        with large.open('wb') as file:
            file.truncate(5*1024*1024+1)
        self.run_job('popup',dict(name='300-3.json',json='{}',copies=[
            {'from':str(fifo),'to':str(self.images/'300-3-fifo')},
            {'from':str(large),'to':str(self.images/'300-3-large')}]))
        self.assertEqual(list(self.images.iterdir()),[])
        self.assertTrue((self.popup/'300-3.json').exists())

    def test_concurrent_helpers_do_not_race_permission_repair_or_replacement(self):
        self.run_job('repair')
        children = []
        for index in range(12):
            action = 'popup' if index % 2 == 0 else 'read-popup'
            job = dict(name=f'{100+index}-1.json', json='{"summary":"PRIVATE_FIXTURE"}', copies=[])
            child = subprocess.Popen([sys.executable, str(HELPER), action, str(self.state)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            child.stdin.write(json.dumps(job)+'\n')
            child.stdin.close()
            children.append(child)
        for child in children:
            self.assertEqual(child.wait(timeout=10), 0, child.stderr.read())
            child.stdout.close()
            child.stderr.close()
        self.assertEqual(len(list(self.popup.glob('*.json'))), 6)
        self.modes_are_private()

    def test_orphan_sweep_and_delete_preserve_referenced_images(self):
        self.run_job('popup',dict(name='100-1.json',json='{}',copies=[]))
        for name in ['100-1-image','999-1-image','100-1-image.tmp','.notification-interrupted']:
            (self.images/name).write_bytes(b'fixture')
        self.run_job('sweep')
        self.assertEqual([p.name for p in self.images.iterdir()],['100-1-image'])
        self.run_job('delete',dict(name='100-1.json'))
        self.assertEqual(list(self.images.iterdir()),[])
        self.assertFalse((self.popup/'100-1.json').exists())
