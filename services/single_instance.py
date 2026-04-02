import atexit
import os
import platform
from pathlib import Path
from typing import TextIO


class SingleInstanceGuard:
    def __init__(self, lock_file_path: str):
        self.lock_file_path = Path(lock_file_path)
        self._lock_handle: TextIO | None = None
        self._locked = False
        self._platform = platform.system()

    def acquire(self) -> bool:
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        lock_handle = open(self.lock_file_path, "a+", encoding="utf-8")

        try:
            self._lock_file(lock_handle)
        except OSError:
            lock_handle.close()
            return False

        lock_handle.seek(0)
        lock_handle.truncate()
        lock_handle.write(str(os.getpid()))
        lock_handle.flush()

        self._lock_handle = lock_handle
        self._locked = True
        atexit.register(self.release)
        return True

    def release(self) -> None:
        if not self._locked:
            return

        try:
            if self._lock_handle is not None:
                try:
                    self._lock_handle.seek(0)
                    self._lock_handle.truncate()
                    self._lock_handle.flush()
                except OSError:
                    pass

                self._unlock_file(self._lock_handle)
                self._lock_handle.close()
        except OSError:
            pass
        finally:
            self._lock_handle = None
            self._locked = False

    def _lock_file(self, lock_handle: TextIO) -> None:
        if self._platform == "Windows":
            import msvcrt

            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
            return

        import fcntl

        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_file(self, lock_handle: TextIO) -> None:
        if self._platform == "Windows":
            import msvcrt

            try:
                lock_handle.seek(0)
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            return

        import fcntl

        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
