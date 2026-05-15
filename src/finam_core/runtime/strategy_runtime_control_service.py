from __future__ import annotations

from typing import Any

from finam_core.contracts.runtime_symbol_mapper import RuntimeSymbolMapper


class StrategyRuntimeControlService:
    """
    Русский комментарий:
    Единый сервис runtime-control.

    Важно:
    - execution работает по raw symbol: BRM6@RTSX;
    - runtime/analytics control работает по continuous symbol: BR_CONT.
    """

    def __init__(self, pg_logger: Any | None = None) -> None:
        self.pg_logger = pg_logger

    def allow_paper(self, symbol: str, qty: float, strategy: str = "default") -> tuple[bool, float, str]:
        try:
            control_symbol = RuntimeSymbolMapper.runtime_symbol(symbol)

            if self.pg_logger is None:
                return True, qty, f"runtime_control_no_pg_logger:control_symbol={control_symbol}"

            conn = getattr(self.pg_logger, "conn", None)

            if conn is None and hasattr(self.pg_logger, "_connect"):
                with self.pg_logger._connect() as runtime_conn:
                    with runtime_conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT allow_trade, watch_only, risk_multiplier, status, reason
                            FROM strategy_runtime_control
                            WHERE symbol = %s AND strategy = %s
                            """,
                            (control_symbol, strategy),
                        )
                        row = cur.fetchone()
            elif conn is not None:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT allow_trade, watch_only, risk_multiplier, status, reason
                        FROM strategy_runtime_control
                        WHERE symbol = %s AND strategy = %s
                        """,
                        (control_symbol, strategy),
                    )
                    row = cur.fetchone()
            else:
                return True, qty, f"runtime_control_no_connection_provider:control_symbol={control_symbol}"

            if row is None:
                return False, 0.0, f"runtime_control_no_data:control_symbol={control_symbol}"

            allow_trade, watch_only, risk_multiplier, status, reason = row

            if bool(watch_only) or not bool(allow_trade):
                return False, 0.0, f"runtime_control_blocked:{status}:{reason}:control_symbol={control_symbol}"

            mult = float(risk_multiplier or 0.0)
            if mult <= 0:
                return False, 0.0, f"runtime_control_zero_risk:{status}:{reason}:control_symbol={control_symbol}"

            adjusted_qty = max(0.0, float(qty) * mult)
            return True, adjusted_qty, f"runtime_control_ok:{status}:mult={mult}:control_symbol={control_symbol}"

        except Exception as exc:
            return True, qty, f"runtime_control_error_soft:{type(exc).__name__}:{exc}"
