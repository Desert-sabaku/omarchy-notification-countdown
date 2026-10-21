#!/usr/bin/env python3
"""Private notification storage. Notification data enters through stdin, never argv."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import tempfile

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_JOB_BYTES = 16 * 1024 * 1024
NAME = re.compile(r'\d+--?\d+\.json\Z')


def owned_regular(path, directory=False):
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if info.st_uid != os.geteuid() or not expected(info.st_mode):
        raise ValueError('Unsafe notification storage entry')
    # Do not chmod through symlinks, including during legacy repair.
    os.chmod(path, 0o700 if directory else 0o600, follow_symlinks=False)


def private_directory(path):
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    owned_regular(path, directory=True)


def prepare(root):
    os.umask(0o077)
    root.parent.mkdir(parents=True, exist_ok=True)
    private_directory(root)  # Close access before inspecting any old contents.
    popup = root / 'notifications'
    history, images = popup / 'history', popup / 'images'
    for directory in [popup, history, images]:
        private_directory(directory)
    for parent, directories, files in os.walk(popup, followlinks=False):
        for name in directories:
            owned_regular(Path(parent) / name, directory=True)
        for name in files:
            path = Path(parent) / name
            owned_regular(path)
            if name.startswith('.notification-'):
                # A killed writer may leave an unpublished private temp file.
                # The lock guarantees it does not belong to an active helper.
                path.unlink()
    settings = root / 'notifications.json'
    if settings.exists() or settings.is_symlink():
        owned_regular(settings)
    return popup, history, images


def atomic_write(path, contents):
    descriptor, temporary = tempfile.mkstemp(prefix='.notification-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(contents)
        os.replace(temporary, path)
        owned_regular(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def valid_name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError('Invalid notification name')
    return value


def image_copy(source, destination):
    def expired(signum, frame):
        raise TimeoutError('Image read deadline exceeded')

    previous = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, 5)
        descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, 'rb') as image:
            if not stat.S_ISREG(os.fstat(image.fileno()).st_mode):
                return
            data = image.read(MAX_IMAGE_BYTES + 1)
        if len(data) <= MAX_IMAGE_BYTES:
            atomic_write(destination, data)
    except (OSError, TimeoutError):
        pass  # Missing, oversized or unreadable images must not block the queue.
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def json_files(directory):
    return sorted((p for p in directory.iterdir() if NAME.fullmatch(p.name)),
                  key=lambda p: int(p.name.split('-', 1)[0]))


def delete_images(images, name):
    stem = name.removesuffix('.json')
    for image in images.iterdir():
        if image.name.startswith(stem + '-'):
            image.unlink()


def trim(history, images, limit):
    limit = max(0, int(limit))
    entries = json_files(history)
    for entry in entries[:max(0, len(entries) - limit)]:
        delete_images(images, entry.name)
        entry.unlink()


@contextmanager
def private_lock(root):
    os.umask(0o077)
    root.parent.mkdir(parents=True, exist_ok=True)
    private_directory(root)
    descriptor = os.open(root / 'notifications.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if info.st_uid != os.geteuid() or not stat.S_ISREG(info.st_mode):
            raise ValueError('Unsafe notification storage lock')
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def perform(action, root, job):
    # Reads/restores can overlap the QML write queue; repair and replace under
    # one private lock so another helper cannot observe half of a migration.
    with private_lock(root):
        return perform_locked(action, root, job)


def perform_locked(action, root, job):
    popup, history, images = prepare(root)
    if action == 'repair':
        return
    if action in ('read-popup', 'read-history'):
        directory = popup if action == 'read-popup' else history
        for entry in json_files(directory):
            sys.stdout.write(entry.read_text().rstrip('\n') + '\n')
        return
    if action == 'settings':
        # Never preserve accidental notification payloads in the DND settings.
        settings = {'version': 3, 'dnd': bool(job['dnd'])}
        atomic_write(root / 'notifications.json', (json.dumps(settings) + '\n').encode())
        return
    if action == 'clear':
        for entry in json_files(history):
            delete_images(images, entry.name)
            entry.unlink()
        return
    if action == 'sweep':
        for image in images.iterdir():
            stem = image.name.rsplit('-', 1)[0]
            if image.name.endswith('.tmp') or image.name.startswith('.notification-') or not (
                    (popup / (stem + '.json')).exists() or (history / (stem + '.json')).exists()):
                image.unlink()
        return
    name = valid_name(job['name'])
    if action in ('popup', 'history'):
        for copy in job.get('copies', []):
            target = Path(copy['to'])
            # Only write into the dedicated private images directory.
            if target.parent != images or not target.name.startswith(name.removesuffix('.json') + '-'):
                raise ValueError('Invalid image destination')
            image_copy(copy['from'], target)
        payload = job['json']
        json.loads(payload)  # Validate without logging the content on errors.
        atomic_write((popup if action == 'popup' else history) / name, (payload + '\n').encode())
        if action == 'history':
            trim(history, images, job['limit'])
    elif action == 'archive':
        source = popup / name
        if source.exists():
            os.replace(source, history / name)
            trim(history, images, job['limit'])
    elif action == 'delete':
        (popup / name).unlink(missing_ok=True)
        delete_images(images, name)
    else:
        raise ValueError('Unknown storage operation')


def main():
    # argv contains only an operation and the application state directory.
    action, state_directory = sys.argv[1:]
    if action in ('repair', 'read-popup', 'read-history'):
        job = {}
    else:
        line = sys.stdin.buffer.readline(MAX_JOB_BYTES + 1)
        if len(line) > MAX_JOB_BYTES or not line.endswith(b'\n'):
            raise ValueError('Invalid input framing')
        job = json.loads(line)
    perform(action, Path(state_directory), job)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Exception strings may contain paths or notification text. Do not log them.
        print('Notification storage operation failed; no payload details logged.', file=sys.stderr)
        sys.exit(1)
