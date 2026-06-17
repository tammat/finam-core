from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


FUTURES_REAL_ALLOWED_AFTER = date(2026, 7, 1)


@dataclass(frozen=True)
class FuturesRealBlockDecisionV1:
    allowed: bool
    reason: str
    symbol: str
    execution_mode: str
    instrument_kind: str
    current_date: date
    allowed_after: date


class FuturesRealBlockGuardV1:
    """Русский комментарий:
    Жёсткий safety guard для запрета real execution по фьючерсам до 01.07.2026.

    Guard не включает торговлю, не отправляет заявки и не меняет runtime.
    Его задача — вернуть allowed=False для futures + real/live режима до контрольной даты.
    """

    def __init__(self, allowed_after: date = FUTURES_REAL_ALLOWED_AFTER) -> None:
        self.allowed_after = allowed_after

    def evaluate(
        self,
        *,
        symbol: str,
        execution_mode: str,
        current_date: Optional[date] = None,
        instrument_kind: Optional[str] = None,
    ) -> FuturesRealBlockDecisionV1:
        today = current_date or date.today()
        normalized_mode = self._normalize(execution_mode)
        kind = self._normalize(instrument_kind or self._infer_instrument_kind(symbol))

        is_real_mode = normalized_mode in {"real", "live", "production"}
        is_futures = kind in {"future", "futures", "forts"}

        if is_futures and is_real_mode and today < self.allowed_after:
            return FuturesRealBlockDecisionV1(
                allowed=False,
                reason="FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01",
                symbol=symbol,
                execution_mode=normalized_mode,
                instrument_kind=kind,
                current_date=today,
                allowed_after=self.allowed_after,
            )

        return FuturesRealBlockDecisionV1(
            allowed=True,
            reason="FUTURES_REAL_BLOCK_GUARD_PASS",
            symbol=symbol,
            execution_mode=normalized_mode,
            instrument_kind=kind,
            current_date=today,
            allowed_after=self.allowed_after,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _infer_instrument_kind(symbol: str) -> str:
        """Русский комментарий:
        Консервативное определение фьючерсов по RTSX/FORTS-символам и типовым кодам.
        Если инструмент не распознан как futures, guard его не блокирует.
        """
        s = str(symbol or "").strip().upper()

        if "@RTSX" in s:
            return "futures"

        futures_prefixes = (
            "BR",      # Brent futures
            "NG",      # Natural gas futures
            "GD",      # Gold futures
            "SI",      # USD/RUB futures
            "USDRUBF", # internal USD/RUB futures alias
        )

        if any(s.startswith(prefix) for prefix in futures_prefixes):
            return "futures"

        return "unknown"


def evaluate_futures_real_block_v1(
    *,
    symbol: str,
    execution_mode: str,
    current_date: Optional[date] = None,
    instrument_kind: Optional[str] = None,
) -> FuturesRealBlockDecisionV1:
    """Русский комментарий:
    Функциональная обёртка для удобного вызова из pipeline/execution gate.
    """
    return FuturesRealBlockGuardV1().evaluate(
        symbol=symbol,
        execution_mode=execution_mode,
        current_date=current_date,
        instrument_kind=instrument_kind,
    )
