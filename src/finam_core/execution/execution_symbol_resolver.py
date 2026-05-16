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
            reason=f"preferred_symbol_from_liquidity_decision:{continuous_symbol}->{preferred}",
        )

    def _continuous_symbol_for(self, symbol: str) -> str | None:
        if symbol in {"BR_CONT", "BRM6@RTSX", "BRN6@RTSX"}:
            return "BR_CONT"

        if symbol in {"NG_CONT", "NGK6@RTSX", "NGM6@RTSX"}:
            return "NG_CONT"

        if symbol in {"USDRUB_CONT", "USDRUBF@RTSX"}:
            return "USDRUB_CONT"

        return None

    def _load_preferred_symbol(self, continuous_symbol: str) -> str | None:
        sql = """
        select preferred_symbol
        from cross_contract_liquidity_decisions
        where continuous_symbol = %s
        order by ts desc
        limit 1
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (continuous_symbol,))
                row = cur.fetchone()

        if not row:
            return None

        return str(row[0])
