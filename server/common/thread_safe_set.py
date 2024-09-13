import threading


class ThreadSafeSet:
    def __init__(self):
        self._set = set()
        self._lock = threading.Lock()

    def add(self, item):
        with self._lock:
            self._set.add(item)
            return len(self._set)

    def remove(self, item):
        with self._lock:
            self._set.remove(item)

    def clear(self):
        with self._lock:
            self._set.clear()

    def __len__(self):
        with self._lock:
            return len(self._set)
