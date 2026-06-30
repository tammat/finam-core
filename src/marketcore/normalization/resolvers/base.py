from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg2.extras

from marketcore.normalization.resolvers.cache import ResolutionCache
from marketcore.normalization.resolvers.metrics import ResolverMetrics


@dataclass
class BaseResolver:
    name: str
    sql: str
    cache: ResolutionCache
    metrics: ResolverMetrics

    def resolve(self, conn, key: str) -> Any | None:
        if self.cache.contains(self.name, key):
            self.metrics.cache_hit += 1
            cached = self.cache.get(self.name, key)
            if cached is None:
                self.metrics.not_found += 1
                return None
            self.metrics.resolved += 1
            return cached

        self.metrics.cache_miss += 1
        self.metrics.sql_queries += 1

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(self.sql, (key, key) if self.sql.count('%s') == 2 else (key,))
            row = cur.fetchone()

        if not row:
            self.cache.set(self.name, key, None)
            self.metrics.not_found += 1
            return None

        value = dict(row)
        self.cache.set(self.name, key, value)
        self.metrics.resolved += 1
        return value
