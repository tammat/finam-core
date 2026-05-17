from __future__ import annotations

from typing import Any

from finam_core.risk.adaptive_regime_filter import (
    AdaptiveRegimeDecision,
    AdaptiveRegimeFilter,
)


SQL = """
with trades_base as (
    select
        symbol,
        side,
        coalesce(commission, 0) as commission,

        case coalesce(payload->>'institutional_flow_regime', 'UNKNOWN')
            when 'ACCUMULATION' then '🟢 Накопление'
            when 'DISTRIBUTION' then '🔴 Распределение'
            when 'TREND_INITIATION' then '🚀 Запуск тренда'
            when 'BREAKOUT_TRAP' then '🪤 Ловушка пробоя'
            when 'INSTITUTIONAL_PARTICIPATION' then '🏦 Активность крупного участника'
            when 'NORMAL_FLOW' then '⚪ Обычная активность'
            else coalesce(payload->>'institutional_flow_regime_ru', '❔ Нет данных')
        end as regime_ru
    from trades
    where qty > 0
),

closed_proxy as (
    select
        symbol,
        regime_ru,
        count(*) filter (where side = 'SELL') as closed_trades,
        round(sum(case when side = 'SELL' then -commission else 0 end)::numeric, 2) as net_pnl_proxy,
        0.0::numeric as winrate_proxy
    from trades_base
    group by symbol, regime_ru
)

select
    symbol,
    regime_ru,
    closed_trades,
    coalesce(net_pnl_proxy, 0) as net_pnl_proxy,
    coalesce(winrate_proxy, 0) as winrate_proxy
from closed_proxy
where symbol = %s
  and regime_ru = %s
limit 1;
"""


class AdaptiveRegimeRepository:
    """Русский комментарий: читает статистику режима по конкретному инструменту из PostgreSQL."""

    def __init__(
        self,
        pg_logger: Any,
        regime_filter: AdaptiveRegimeFilter | None = None,
    ) -> None:
        self.pg_logger = pg_logger
        self.regime_filter = regime_filter or AdaptiveRegimeFilter()

    def evaluate_regime(self, regime_ru: str, symbol: str | None = None) -> AdaptiveRegimeDecision:
        regime_ru = str(regime_ru or "❔ Нет данных")
        symbol = str(symbol or "")

        if not symbol:
            return self.regime_filter.evaluate(
                regime=regime_ru,
                closed_trades=0,
                net_pnl=0.0,
                winrate=0.0,
            )

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(SQL, (symbol, regime_ru))
                row = cur.fetchone()

        if not row:
            return self.regime_filter.evaluate(
                regime=regime_ru,
                closed_trades=0,
                net_pnl=0.0,
                winrate=0.0,
            )

        _, regime, closed_trades, net_pnl, winrate = row

        return self.regime_filter.evaluate(
            regime=str(regime),
            closed_trades=int(closed_trades or 0),
            net_pnl=float(net_pnl or 0.0),
            winrate=float(winrate or 0.0),
        )
