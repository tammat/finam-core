from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionSymbolDecision:
    requested_symbol: str
    execution_symbol: str
    continuous_symbol: str | None
    reason: str


class ExecutionSymbolResolver:
    """Русский комментарий: переводит continuous/rollover context в конкретный контракт для execution."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def resolve(self, symbol: str) -> ExecutionSymbolDecision:
        requested = str(symbol or "")

        continuous_symbol = self._continuous_symbol_for(requested)

        if not continuous_symbol:
            return ExecutionSymbolDecision(
                requested_symbol=requested,
                execution_symbol=requested,
                continuous_symbol=None,
                reason="no_continuous_mapping",
            )

        preferred = self._load_preferred_symbol(continuous_symbol)

        if not preferred:
            return ExecutionSymbolDecision(
                requested_symbol=requested,
                execution_symbol=requested,
                continuous_symbol=continuous_symbol,
                reason=f"no_preferred_symbol_for:{continuous_symbol}",
            )

        return ExecutionSymbolDecision(
            requested_symbol=requested,
            execution_symbol=preferred,
            continuous_symbol=continuous_symbol,
            reason=f"autonomous_roll_decision:{continuous_symbol}->{preferred}",
        )

    def _continuous_symbol_for(self, symbol: str) -> str | None:
        base=symbol.split("@",1)[0]
        if symbol == "BR_CONT" or (symbol.endswith("@RTSX") and base.startswith("BR")):
            return "BR_CONT"

        if symbol == "NG_CONT" or (symbol.endswith("@RTSX") and base.startswith("NG")):
            return "NG_CONT"

        if symbol in {"USDRUB_CONT", "USDRUBF@RTSX"}:
            return "USDRUB_CONT"

        if symbol in {"CNYRUB_CONT", "CNYRUBF@RTSX"}:
            return "CNYRUB_CONT"

        # GLDRUBF — каноническое имя исследовательского потока,
        # GDU6 — фактический биржевой контракт исполнения.
        if symbol in {"GOLD_CONT", "GLDRUBF@RTSX", "GDU6@RTSX"}:
            return "GOLD_CONT"

        return None

    def _load_preferred_symbol(self, continuous_symbol: str) -> str | None:
        alias_sql = """
        select execution_symbol
        from analytics.futures_symbol_alias_v1
        where canonical_symbol = %s
          and enabled
        limit 1
        """
        sql = """
        select selected_symbol
        from analytics.futures_roll_decision_v1
        where root_symbol = %s
        order by created_at desc
        limit 1
        """

        root=continuous_symbol.removesuffix("_CONT")

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(alias_sql, (continuous_symbol,))
                    alias_row = cur.fetchone()
                    if alias_row:
                        return str(alias_row[0])
                except Exception:
                    # Совместимость до применения миграции 204.
                    conn.rollback()
                cur.execute(sql, (root,))
                row = cur.fetchone()

        if not row:
            return None

        return str(row[0])
