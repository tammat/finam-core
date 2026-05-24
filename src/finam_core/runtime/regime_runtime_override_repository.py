from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class RuntimeRegimeOverrideState:
    strategy: str
    root_symbol: str
    regime: str
    runtime_action: str
    max_position_size: float
    allowed_execution_mode: str
    risk_multiplier: float
    cooldown_sec: int
    stop_take_profile: str
    reason: str


class RuntimeRegimeOverrideRepository:
    """Русский комментарий: читает runtime ограничения, рассчитанные research/runtime слоями."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def get_override(
        self,
        *,
        strategy: str,
        root_symbol: str,
        regime: str,
    ) -> RuntimeRegimeOverrideState | None:
        sql = """
        SELECT
            strategy,
            root_symbol,
            regime,
            runtime_action,
            max_position_size,
            allowed_execution_mode,
            risk_multiplier,
            cooldown_sec,
            stop_take_profile,
            reason
        FROM runtime_regime_overrides
        WHERE strategy = %s
          AND root_symbol = %s
          AND regime = %s
        ORDER BY created_at DESC
        LIMIT 1;
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (strategy, root_symbol, regime))
                row = cur.fetchone()

        if row is None:
            return None

        return RuntimeRegimeOverrideState(
            strategy=str(row[0]),
            root_symbol=str(row[1]),
            regime=str(row[2]),
            runtime_action=str(row[3]),
            max_position_size=float(row[4] or 0),
            allowed_execution_mode=str(row[5] or ""),
            risk_multiplier=float(row[6] or 0),
            cooldown_sec=int(row[7] or 0),
            stop_take_profile=str(row[8] or ""),
            reason=str(row[9] or ""),
        )
