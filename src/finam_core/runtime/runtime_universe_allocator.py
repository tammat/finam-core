from __future__ import annotations

import json
from datetime import date
from typing import Any

from finam_core.analytics.strategy_rank_weight_provider import StrategyRankWeightProvider


class RuntimeUniverseAllocator:
    """Русский комментарий: формирует фактический runtime-universe из dynamic_watchlist."""

    def __init__(self, pg_logger: Any, weight_provider: Any | None = None) -> None:
        self.pg_logger = pg_logger
        self.weight_provider = weight_provider or StrategyRankWeightProvider(pg_logger)

    def allocate(
        self,
        *,
        max_symbols: int = 5,
        min_score: float = 0.35,
    ) -> int:
        sql = """
        with selected as (
            select
                symbol,
                strategy,
                regime,
                score,
                priority,
                reason,
                raw_json
            from dynamic_watchlist
            where is_active = true
              and source = 'freshness_adjusted_scoring_v2'
              and score >= %s
              and strategy <> 'NO_TRADE'
            order by score desc, priority desc, updated_at desc
            limit %s
        ),
        upserted as (
            insert into runtime_active_universe (
                symbol, strategy, regime, score, priority,
                is_enabled, allocated_at, last_seen_at,
                disabled_at, disable_reason, source, raw_json, updated_at
            )
            select
                symbol, strategy, regime, score, priority,
                true, now(), now(),
                null, null, 'runtime_universe_allocator',
                raw_json || jsonb_build_object('allocator_reason', reason),
                now()
            from selected
            on conflict (symbol) do update set
                strategy = excluded.strategy,
                regime = excluded.regime,
                score = excluded.score,
                priority = excluded.priority,
                is_enabled = true,
                last_seen_at = now(),
                disabled_at = null,
                disable_reason = null,
                raw_json = excluded.raw_json,
                updated_at = now()
            returning symbol
        )
        update runtime_active_universe rau
        set
            is_enabled = false,
            disabled_at = now(),
            disable_reason = 'not_selected_by_runtime_allocator',
            updated_at = now()
        where rau.symbol not in (select symbol from selected)
          and rau.is_enabled = true;

        select count(*)
        from runtime_active_universe
        where is_enabled = true;
        """

        today = date.today()

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (min_score, max_symbols))
                row = cur.fetchone()
                active_count = int(row[0] or 0)
            conn.commit()

        return active_count
