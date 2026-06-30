from __future__ import annotations

from dataclasses import dataclass, field

import psycopg2

from marketcore.normalization.resolvers.base import BaseResolver
from marketcore.normalization.resolvers.cache import ResolutionCache
from marketcore.normalization.resolvers.metrics import ResolverMetrics


@dataclass
class ResolverRegistry:
    conn: psycopg2.extensions.connection
    cache: ResolutionCache = field(default_factory=ResolutionCache)
    metrics: dict[str, ResolverMetrics] = field(default_factory=dict)

    def _metrics(self, name: str) -> ResolverMetrics:
        self.metrics.setdefault(name, ResolverMetrics())
        return self.metrics[name]

    def resolver(self, name: str, sql: str) -> BaseResolver:
        return BaseResolver(
            name=name,
            sql=sql,
            cache=self.cache,
            metrics=self._metrics(name),
        )

    @property
    def source_system(self) -> BaseResolver:
        return self.resolver(
            "source_system",
            """
            SELECT id, entity_code, entity_name
            FROM warehouse.normalized_source_system_v1
            WHERE entity_code=%s
            LIMIT 1
            """,
        )

    @property
    def symbol_alias(self) -> BaseResolver:
        return self.resolver(
            "symbol_alias",
            """
            SELECT id, entity_code, instrument_id, contract_id, source_system_id
            FROM warehouse.normalized_symbol_alias_v1
            WHERE source_system_id = split_part(%s, '::', 1)::bigint
              AND entity_code = split_part(%s, '::', 2)
            LIMIT 1
            """,
        )

    @property
    def instrument(self) -> BaseResolver:
        return self.resolver(
            "instrument",
            """
            SELECT
                id,
                entity_code,
                asset_id
            FROM warehouse.normalized_instrument_v1
            WHERE id = %s::bigint
            LIMIT 1
            """,
        )

    @property
    def contract(self) -> BaseResolver:
        return self.resolver(
            "contract",
            """
            SELECT
                id,
                entity_code,
                instrument_id,
                market_id
            FROM warehouse.normalized_contract_v1
            WHERE id = %s::bigint
            LIMIT 1
            """,
        )

    @property
    def timeframe(self) -> BaseResolver:
        return self.resolver(
            "timeframe",
            """
            SELECT id, entity_code
            FROM warehouse.normalized_timeframe_v1
            WHERE entity_code=%s
            LIMIT 1
            """,
        )

    @property
    def event_type(self) -> BaseResolver:
        return self.resolver(
            "event_type",
            """
            SELECT id, entity_code, event_domain
            FROM warehouse.normalized_event_type_v1
            WHERE entity_code=%s
            LIMIT 1
            """,
        )

    @property
    def quality_status(self) -> BaseResolver:
        return self.resolver(
            "quality_status",
            """
            SELECT id, entity_code
            FROM warehouse.normalized_quality_status_v1
            WHERE entity_code=%s
            LIMIT 1
            """,
        )
