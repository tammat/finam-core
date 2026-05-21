from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class ExitPolicyAdvice:
    symbol: str
    strategy: str
    timeframe: str
    policy: str
    take_distance: float
    stop_distance: float
    profit_factor: float
    net_pnl: float
    max_drawdown: float
    winrate: float
    source: str = "analytics_exit_policy_selected"


class RuntimeExitPolicyAdvisor:
    """
    Русский комментарий:
    Advisory-only слой.

    Он только читает выбранный exit policy из analytics_exit_policy_selected
    и возвращает рекомендацию по take/stop distance.

    Важно:
    - не отправляет заявки;
    - не меняет RiskEngine;
    - не заменяет стратегию;
    - не является execution route.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def get_advice(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> ExitPolicyAdvice | None:
        sql = """
        SELECT
            symbol,
            strategy,
            timeframe,
            selected_policy,
            take_distance,
            stop_distance,
            profit_factor,
            net_pnl,
            max_drawdown,
            winrate
        FROM analytics_exit_policy_selected
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
          AND is_active = TRUE
        ORDER BY selected_at DESC
        LIMIT 1
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, strategy, timeframe))
                row = cur.fetchone()

        if row is None:
            return None

        return ExitPolicyAdvice(
            symbol=str(row[0]),
            strategy=str(row[1]),
            timeframe=str(row[2]),
            policy=str(row[3]),
            take_distance=float(row[4]),
            stop_distance=float(row[5]),
            profit_factor=float(row[6]),
            net_pnl=float(row[7]),
            max_drawdown=float(row[8]),
            winrate=float(row[9]),
        )
