from __future__ import annotations

from typing import Any


class RegimeRuntimeControlService:
    """
    Русский комментарий:
    Runtime-control по связке symbol + strategy + regime.
    Глобальный strategy_runtime_control остаётся первым safety layer.
    """

    def __init__(self, pg_logger: Any | None = None) -> None:
        self.pg_logger = pg_logger

    def allow_regime(
        self,
        symbol: str,
        strategy: str,
        regime: str | None,
        qty: float,
    ) -> tuple[bool, float, str]:
        regime_key = str(regime or "UNKNOWN")

        try:
            if self.pg_logger is None:
                return True, qty, f"regime_control_no_pg_logger:regime={regime_key}"

            conn = getattr(self.pg_logger, "conn", None)

            if conn is None and hasattr(self.pg_logger, "_connect"):
                with self.pg_logger._connect() as runtime_conn:
                    with runtime_conn.cursor() as cur:
                        cur.execute(
                            """
                            select allow_trade, watch_only, risk_multiplier, status, reason
                            from strategy_runtime_regime_control
                            where symbol = %s and strategy = %s and regime = %s
                            """,
                            (symbol, strategy, regime_key),
                        )
                        row = cur.fetchone()
            elif conn is not None:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select allow_trade, watch_only, risk_multiplier, status, reason
                        from strategy_runtime_regime_control
                        where symbol = %s and strategy = %s and regime = %s
                        """,
                        (symbol, strategy, regime_key),
                    )
                    row = cur.fetchone()
            else:
                return True, qty, f"regime_control_no_connection:regime={regime_key}"

            if row is None:
                return True, qty, f"regime_control_no_data_soft:regime={regime_key}"

            allow_trade, watch_only, risk_multiplier, status, reason = row

            if bool(watch_only) or not bool(allow_trade):
                return False, 0.0, f"regime_control_blocked:{status}:{reason}:regime={regime_key}"

            mult = float(risk_multiplier or 0.0)
            if mult <= 0:
                return False, 0.0, f"regime_control_zero_risk:{status}:{reason}:regime={regime_key}"

            return True, max(0.0, float(qty) * mult), f"regime_control_ok:{status}:mult={mult}:regime={regime_key}"

        except Exception as exc:
            return True, qty, f"regime_control_error_soft:{type(exc).__name__}:{exc}"
