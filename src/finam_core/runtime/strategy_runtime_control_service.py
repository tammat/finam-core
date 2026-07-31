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

    @staticmethod
    def _lookup_control(cur: Any, candidates: list[tuple[str, str]]) -> tuple[Any | None, str, str]:
        seen: set[tuple[str, str]] = set()
        for lookup_symbol, lookup_strategy in candidates:
            key = (str(lookup_symbol), str(lookup_strategy))
            if key in seen:
                continue
            seen.add(key)
            cur.execute(
                """
                SELECT allow_trade, watch_only, risk_multiplier, status, reason
                FROM strategy_runtime_control
                WHERE symbol = %s AND strategy = %s
                """,
                key,
            )
            row = cur.fetchone()
            if row is not None:
                return row, key[0], key[1]
        return None, "", ""

    @staticmethod
    def _scope_bootstrap_allowed(cur: Any, portfolio_scope: str | None) -> bool:
        """Возвращает разрешение на накопление *новой* изолированной когорты.

        Политика хранится в БД, чтобы V5 не наследовала статистическую
        блокировку старого V2/V4-контура после нормализации символа.
        Это не отменяет остальные входные шлюзы pipeline: режим, риск,
        издержки, стакан и допуск стратегии проверяются отдельно.
        """
        if not portfolio_scope:
            return False
        cur.execute(
            """
            SELECT allow_scope_bootstrap
            FROM analytics.paper_scope_runtime_policy_v1
            WHERE scope_code = %s
              AND enabled = true
            """,
            (portfolio_scope,),
        )
        row = cur.fetchone()
        return bool(row and row[0])

    @staticmethod
    def _has_promoted_oos_edge(cur: Any) -> bool:
        """Only an explicitly promoted OOS result removes the Paper safety cap."""
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM analytics.edge_oos_result_v1
                WHERE verdict_code = 'OOS_PASS'
                  AND promotion_allowed = true
            )
            """
        )
        row = cur.fetchone()
        return bool(row and row[0])

    def allow_paper(
        self,
        symbol: str,
        qty: float,
        strategy: str = "default",
        portfolio_scope: str | None = None,
    ) -> tuple[bool, float, str]:
        try:
            control_symbol = RuntimeSymbolMapper.runtime_symbol(symbol)
            candidates = [
                (control_symbol, strategy),
                (symbol, strategy),
                (symbol, "default"),
                (control_symbol, "default"),
            ]

            if self.pg_logger is None:
                return True, qty, f"runtime_control_no_pg_logger:control_symbol={control_symbol}"

            conn = getattr(self.pg_logger, "conn", None)

            if conn is None and hasattr(self.pg_logger, "_connect"):
                with self.pg_logger._connect() as runtime_conn:
                    with runtime_conn.cursor() as cur:
                        if self._scope_bootstrap_allowed(cur, portfolio_scope):
                            promoted = self._has_promoted_oos_edge(cur)
                            safe_qty = float(qty) if promoted else min(abs(float(qty)), 1.0)
                            reason = (
                                f"runtime_control_scope_bootstrap:{portfolio_scope}"
                                if promoted
                                else f"runtime_control_experimental_cap:no_promoted_oos:{portfolio_scope}"
                            )
                            return True, safe_qty, reason
                        row, matched_symbol, matched_strategy = self._lookup_control(cur, candidates)
            elif conn is not None:
                with conn.cursor() as cur:
                    if self._scope_bootstrap_allowed(cur, portfolio_scope):
                        promoted = self._has_promoted_oos_edge(cur)
                        safe_qty = float(qty) if promoted else min(abs(float(qty)), 1.0)
                        reason = (
                            f"runtime_control_scope_bootstrap:{portfolio_scope}"
                            if promoted
                            else f"runtime_control_experimental_cap:no_promoted_oos:{portfolio_scope}"
                        )
                        return True, safe_qty, reason
                    row, matched_symbol, matched_strategy = self._lookup_control(cur, candidates)
            else:
                return True, qty, f"runtime_control_no_connection_provider:control_symbol={control_symbol}"

            if row is None:
                return False, 0.0, f"runtime_control_no_data:control_symbol={control_symbol}"

            allow_trade, watch_only, risk_multiplier, status, reason = row

            if bool(watch_only) or not bool(allow_trade):
                return False, 0.0, (
                    f"runtime_control_blocked:{status}:{reason}:control_symbol={control_symbol}:"
                    f"matched_symbol={matched_symbol}:matched_strategy={matched_strategy}"
                )

            mult = float(risk_multiplier or 0.0)
            if mult <= 0:
                return False, 0.0, (
                    f"runtime_control_zero_risk:{status}:{reason}:control_symbol={control_symbol}:"
                    f"matched_symbol={matched_symbol}:matched_strategy={matched_strategy}"
                )

            adjusted_qty = max(0.0, float(qty) * mult)
            return True, adjusted_qty, (
                f"runtime_control_ok:{status}:mult={mult}:control_symbol={control_symbol}:"
                f"matched_symbol={matched_symbol}:matched_strategy={matched_strategy}"
            )

        except Exception as exc:
            return True, qty, f"runtime_control_error_soft:{type(exc).__name__}:{exc}"
