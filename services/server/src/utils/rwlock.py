import contextlib
import threading


class RWLock:
    def __init__(self):
        self._condition = threading.Condition()
        self._readers = 0
        self._writers = 0

    @contextlib.contextmanager
    def read_lock(self):
        with self._condition:
            while self._writers > 0:
                self._condition.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                if self._readers == 0:
                    self._condition.notify_all()

    @contextlib.contextmanager
    def write_lock(self):
        with self._condition:
            while self._writers > 0 or self._readers > 0:
                self._condition.wait()
            self._writers += 1
        try:
            yield
        finally:
            with self._condition:
                self._writers -= 1
                self._condition.notify_all()
