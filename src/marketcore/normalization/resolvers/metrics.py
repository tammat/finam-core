from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResolverMetrics:
    cache_hit: int = 0
    cache_miss: int = 0
    sql_queries: int = 0
    resolved: int = 0
    not_found: int = 0
