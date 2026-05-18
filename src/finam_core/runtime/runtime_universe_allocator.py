from __future__ import annotations

import json
from datetime import date
from typing import Any

from finam_core.analytics.strategy_rank_weight_provider import StrategyRankWeightProvider
from finam_core.runtime.runtime_allocator_decision_logger import RuntimeAllocatorDecisionLogger
from finam_core.runtime.runtime_strategy_gate_provider import RuntimeStrategyGateProvider


class RuntimeUniverseAllocator:
    """Русский комментарий: формирует фактический runtime-universe из dynamic_watchlist."""

    def __init__(self, pg_logger: Any, weight_provider: Any | None = None) -> None:
        self.pg_logger = pg_logger
        self.weight_provider = weight_provider or StrategyRankWeightProvider(pg_logger)
        self.decision_logger = RuntimeAllocatorDecisionLogger(pg_logger)
        self.strategy_gate_provider = RuntimeStrategyGateProvider(pg_logger)

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

        today = date.today()

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
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
                    ''',
                    (min_score, max_symbols * 5),
                )

                rows = cur.fetchall()

                weighted_rows = []

                for row in rows:
                    (
                        symbol,
                        strategy,
                        regime,
                        score,
                        priority,
                        reason,
                        raw_json,
                    ) = row

                    allowed, gate_reason = self.strategy_gate_provider.allows(
                        trade_date=today,
                        strategy=str(strategy),
                        symbol=str(symbol),
                        timeframe="unknown",
                    )

                    weight = self.weight_provider.get_weight(
                        trade_date=today,
                        strategy=str(strategy),
                        symbol=str(symbol),
                        timeframe="unknown",
                    )

                    if not allowed:
                        weight = 0

                    effective_score = float(score or 0) * float(weight)

                    weighted_rows.append(
                        (
                            effective_score,
                            symbol,
                            strategy,
                            regime,
                            score,
                            priority,
                            reason,
                            raw_json,
                            weight,
                        )
                    )

                weighted_rows.sort(key=lambda x: x[0], reverse=True)

                selected = weighted_rows[:max_symbols]
                selected_keys = {(row[1], row[2]) for row in selected}

                for (
                    effective_score,
                    symbol,
                    strategy,
                    regime,
                    score,
                    priority,
                    reason,
                    raw_json,
                    weight,
                ) in weighted_rows:
                    if float(weight) <= 0 or float(effective_score) <= 0:
                        selected_flag = False
                        decision_reason = "rejected_by_weight"
                    elif (symbol, strategy) in selected_keys:
                        selected_flag = True
                        decision_reason = "selected_by_effective_score_limit"
                    else:
                        selected_flag = False
                        decision_reason = "rejected_by_limit"

                    self.decision_logger.log_decision(
                        symbol=str(symbol),
                        strategy=str(strategy),
                        regime=str(regime),
                        base_score=float(score or 0),
                        strategy_weight=float(weight),
                        effective_score=float(effective_score),
                        selected=selected_flag,
                        decision_reason=decision_reason,
                        raw_json={
                            "priority": priority,
                            "allocator_reason": reason,
                            "gate_reason": gate_reason,
                        },
                    )

                cur.execute("delete from runtime_active_universe")

                for (
                    effective_score,
                    symbol,
                    strategy,
                    regime,
                    score,
                    priority,
                    reason,
                    raw_json,
                    weight,
                ) in selected:

                    payload = raw_json or {}
                    payload["base_score"] = float(score or 0)
                    payload["strategy_weight"] = float(weight)
                    payload["effective_score"] = float(effective_score)

                    cur.execute(
                        '''
                        insert into runtime_active_universe (
                            symbol,
                            strategy,
                            regime,
                            score,
                            priority,
                            is_enabled,
                            allocated_at,
                            last_seen_at,
                            source,
                            raw_json,
                            updated_at
                        )
                        values (
                            %s,%s,%s,%s,%s,
                            true,
                            now(),
                            now(),
                            'runtime_universe_allocator_v2',
                            %s::jsonb,
                            now()
                        )
                        ''',
                        (
                            symbol,
                            strategy,
                            regime,
                            effective_score,
                            priority,
                            json.dumps(payload),
                        ),
                    )

                active_count = len(selected)

            conn.commit()

        print(
            f"RUNTIME_ALLOCATOR_V2_OK active_count={active_count}",
            flush=True,
        )

        return active_count
