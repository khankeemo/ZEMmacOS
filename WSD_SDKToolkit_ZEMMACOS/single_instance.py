"""Single instance lock — prevents duplicate process controllers"""
import os
import sys
import tempfile
import atexit


class SingleInstance:
    _lock_file: str = ''
    _fd: int = -1

    def __init__(self, lock_name: str):
        self._lock_file = os.path.join(
            tempfile.gettempdir(),
            f'{lock_name}.opencode.lock'
        )
        try:
            self._fd = os.open(self._lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            atexit.register(self._release)
        except FileExistsError:
            print(f'Another instance of {lock_name} is already running.')
            print('Only one process may control the licensing workflow.')
            sys.exit(1)
        except Exception as e:
            print(f'Failed to acquire instance lock: {e}')
            sys.exit(1)

    def _release(self) -> None:
        try:
            os.close(self._fd)
        except Exception:
            pass
        try:
            os.unlink(self._lock_file)
        except Exception:
            pass
