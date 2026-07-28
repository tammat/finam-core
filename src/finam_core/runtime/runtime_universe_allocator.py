from __future__ import annotations

import json
from datetime import date
from typing import Any

from finam_core.analytics.strategy_rank_weight_provider import StrategyRankWeightProvider
from finam_core.runtime.runtime_allocator_decision_logger import RuntimeAllocatorDecisionLogger
from finam_core.runtime.runtime_strategy_gate_provider import RuntimeStrategyGateProvider
from finam_core.runtime.runtime_strategy_cooldown_provider import RuntimeStrategyCooldownProvider


class RuntimeUniverseAllocator:
    """Русский комментарий: формирует фактический runtime-universe из dynamic_watchlist."""

    def __init__(self, pg_logger: Any, weight_provider: Any | None = None) -> None:
        self.pg_logger = pg_logger
        self.weight_provider = weight_provider or StrategyRankWeightProvider(pg_logger)
        self.decision_logger = RuntimeAllocatorDecisionLogger(pg_logger)
        self.strategy_gate_provider = RuntimeStrategyGateProvider(pg_logger)
        self.strategy_cooldown_provider = RuntimeStrategyCooldownProvider(pg_logger)

    def allocate(
        self,
        *,
        max_symbols: int = 5,
        min_score: float = 0.35,
    ) -> int:
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

                    cooldown_allowed, cooldown_reason = self.strategy_cooldown_provider.allows(
                        strategy=str(strategy),
                        symbol=str(symbol),
                        timeframe="unknown",
                    )

                    allowed = allowed and cooldown_allowed
                    gate_reason = f"{gate_reason}|{cooldown_reason}"

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
                            "cooldown_reason": cooldown_reason,
                        },
                    )

                # Русский комментарий:
                # Не удаляем ручные forward-accumulation seed-строки.
                # Они нужны для research-only накопления статистики по контрактам,
                # которые allocator пока не выбирает автоматически.
                cur.execute("""
                    delete from runtime_active_universe
                    where coalesce(source, '') not in (
                        'manual_forward_accumulation_seed',
                        'manual_forward_accumulation',
                        'db_strategy_assignment_v1'
                    )
                """)

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

                    # Акции входят в runtime только вместе с двумя режимными
                    # политиками. DB-функция записывает политики первой и
                    # активирует инструмент в той же транзакции.
                    if str(symbol).endswith("@MISX"):
                        range_strategy = "MEAN_REVERSION_EQUITY"
                        range_generator = "EQUITY_MEAN_REVERSION_GENERATOR_V1"
                        trend_strategy = "VOLATILITY_BREAKOUT_EQUITY"
                        trend_generator = "EQUITY_VOLATILITY_BREAKOUT_GENERATOR_V1"
                        asset_group = "EQUITY"
                    else:
                        # Не придумываем fallback для фьючерсов. Их стратегия
                        # обязана быть явно назначена в БД.
                        cur.execute(
                            '''
                            select asset_group, strategy_code, generator_code, timeframe
                            from analytics.runtime_strategy_assignment_v1
                            where symbol=%s and enabled
                            order by priority desc, updated_at desc
                            limit 1
                            ''',
                            (symbol,),
                        )
                        assignment = cur.fetchone()
                        if assignment is None:
                            self.decision_logger.log_decision(
                                symbol=str(symbol),
                                strategy=str(strategy),
                                regime=str(regime),
                                base_score=float(score or 0),
                                strategy_weight=float(weight),
                                effective_score=float(effective_score),
                                selected=False,
                                decision_reason="rejected_missing_atomic_strategy_policy",
                                raw_json={"allocator_reason": reason},
                            )
                            continue
                        asset_group, assigned_strategy, assigned_generator, timeframe = assignment
                        range_strategy = trend_strategy = assigned_strategy
                        range_generator = trend_generator = assigned_generator

                    cur.execute(
                        '''
                        select analytics.activate_instrument_with_strategy_policy_v2(
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        ''',
                        (
                            symbol,
                            "M5" if str(symbol).endswith("@MISX") else timeframe,
                            asset_group,
                            range_strategy,
                            range_generator,
                            trend_strategy,
                            trend_generator,
                            priority,
                            effective_score,
                            "Атомарный выбор runtime allocator",
                        ),
                    )
                    cur.execute(
                        '''
                        update runtime_active_universe
                        set allocated_at=now(), last_seen_at=now(),
                            source='runtime_universe_allocator_v2',
                            raw_json=%s::jsonb, updated_at=now()
                        where symbol=%s
                        ''',
                        (json.dumps(payload), symbol),
                    )

                # DB-назначения являются отдельным контрактом, а не fallback.
                # В частности, так фьючерсные BR/NG генераторы не конкурируют
                # с акциями за общий лимит allocator-а.
                cur.execute(
                    '''
                    select symbol,timeframe,asset_group,strategy_code,generator_code,
                           priority,assignment_reason
                    from analytics.runtime_strategy_assignment_v1
                    where enabled
                    '''
                )
                for (
                    assigned_symbol,
                    assigned_timeframe,
                    asset_group,
                    assigned_strategy,
                    assigned_generator,
                    assigned_priority,
                    assignment_reason,
                ) in cur.fetchall():
                    if str(asset_group).upper() == "EQUITY":
                        range_strategy = "MEAN_REVERSION_EQUITY"
                        range_generator = "EQUITY_MEAN_REVERSION_GENERATOR_V1"
                        trend_strategy = "VOLATILITY_BREAKOUT_EQUITY"
                        trend_generator = "EQUITY_VOLATILITY_BREAKOUT_GENERATOR_V1"
                    else:
                        range_strategy = trend_strategy = assigned_strategy
                        range_generator = trend_generator = assigned_generator
                    cur.execute(
                        '''
                        select analytics.activate_instrument_with_strategy_policy_v2(
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        ''',
                        (
                            assigned_symbol,
                            assigned_timeframe,
                            asset_group,
                            range_strategy,
                            range_generator,
                            trend_strategy,
                            trend_generator,
                            assigned_priority,
                            float(assigned_priority or 0) / 100.0,
                            assignment_reason,
                        ),
                    )
                cur.execute("select count(*) from runtime_active_universe where is_enabled")
                active_count = int(cur.fetchone()[0])

            conn.commit()

        print(
            f"RUNTIME_ALLOCATOR_V2_OK active_count={active_count}",
            flush=True,
        )

        return active_count
