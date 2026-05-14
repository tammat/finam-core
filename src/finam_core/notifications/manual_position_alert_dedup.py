# -*- coding: utf-8 -*-

from __future__ import annotations

import time


class ManualPositionAlertDedup:
    def __init__(self, ttl_sec: float = 3600.0):
        self.ttl_sec = ttl_sec
        self._cache: dict[str, float] = {}

    def should_send(self, key: str) -> bool:
        now = time.time()

        expired = [
            k for k, ts in self._cache.items()
            if now - ts > self.ttl_sec
        ]

        for k in expired:
            self._cache.pop(k, None)

        ts = self._cache.get(key)

        if ts is not None and now - ts <= self.ttl_sec:
            return False

        self._cache[key] = now
        return True
