# dashboard/backend/app/utils/cache.py
import functools
import threading
import time


class TTLCache:
    def __init__(self, ttl_seconds=30):
        self.ttl_seconds = ttl_seconds
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.monotonic() > expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key, value):
        with self._lock:
            self._store[key] = (value, time.monotonic() + self.ttl_seconds)

    def clear(self):
        with self._lock:
            self._store.clear()


def ttl_cache(ttl_seconds=30):
    cache = TTLCache(ttl_seconds)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            cached = cache.get(key)
            if cached is not None:
                return cached
            value = func(*args, **kwargs)
            cache.set(key, value)
            return value

        return wrapper

    decorator.cache = cache
    return decorator
