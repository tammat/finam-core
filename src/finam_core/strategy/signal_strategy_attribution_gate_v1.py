from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyAttributionDecisionV1:
    allowed: bool
    strategy: str | None
    timeframe: str | None
    continuous_symbol: str | None
    reason: str
    source: str
    discovery_required: bool


class SignalStrategyAttributionGateV1:
    """
    Русский комментарий:
    Gate определяет стратегию до записи сделки в trades.

    Рыночные данные сами по себе не являются стратегией.
    Источник истины — сигнал и его контекст: reason, strategy, timeframe,
    symbol, continuous_symbol, execution_type.

    Если соответствие сигнал -> стратегия не найдено, сделку нельзя писать
    как обычную trade-запись. Нужно создать событие на разбор сигнала.
    """

    def resolve(self, *, symbol: str, payload: dict[str, Any] | None) -> StrategyAttributionDecisionV1:
        payload = payload or {}

        explicit = self._resolve_explicit_payload(symbol=symbol, payload=payload)
        if explicit.allowed:
            return explicit

        inferred = self._resolve_from_signal_reason(symbol=symbol, payload=payload)
        if inferred.allowed:
            return inferred

        return StrategyAttributionDecisionV1(
            allowed=False,
            strategy=None,
            timeframe=None,
            continuous_symbol=self._default_continuous_symbol(symbol),
            reason="SIGNAL_STRATEGY_UNRESOLVED",
            source="unresolved_signal_context",
            discovery_required=True,
        )

    def _resolve_explicit_payload(
        self,
        *,
        symbol: str,
        payload: dict[str, Any],
    ) -> StrategyAttributionDecisionV1:
        nested = payload.get("payload")
        if not isinstance(nested, dict):
            nested = {}

        strategy = self._first_non_empty(
            payload.get("strategy"),
            nested.get("strategy"),
        )
        timeframe = self._first_non_empty(
            payload.get("timeframe"),
            nested.get("timeframe"),
        )
        continuous_symbol = self._first_non_empty(
            payload.get("continuous_symbol"),
            nested.get("continuous_symbol"),
            self._default_continuous_symbol(symbol),
        )

        if strategy and timeframe and continuous_symbol:
            return StrategyAttributionDecisionV1(
                allowed=True,
                strategy=strategy,
                timeframe=timeframe,
                continuous_symbol=continuous_symbol,
                reason="STRATEGY_ATTRIBUTED_FROM_PAYLOAD",
                source="payload",
                discovery_required=False,
            )

        return StrategyAttributionDecisionV1(
            allowed=False,
            strategy=strategy,
            timeframe=timeframe,
            continuous_symbol=continuous_symbol,
            reason="PAYLOAD_CONTEXT_INCOMPLETE",
            source="payload",
            discovery_required=True,
        )

    def _resolve_from_signal_reason(
        self,
        *,
        symbol: str,
        payload: dict[str, Any],
    ) -> StrategyAttributionDecisionV1:
        nested = payload.get("payload")
        if not isinstance(nested, dict):
            nested = {}

        reason = self._first_non_empty(
            payload.get("reason"),
            nested.get("reason"),
            payload.get("signal_reason"),
            nested.get("signal_reason"),
        )

        timeframe = self._first_non_empty(
            payload.get("timeframe"),
            nested.get("timeframe"),
            "LIVE",
        )

        continuous_symbol = self._first_non_empty(
            payload.get("continuous_symbol"),
            nested.get("continuous_symbol"),
            self._default_continuous_symbol(symbol),
        )

        reason_text = str(reason or "").upper()
        symbol_text = symbol.upper()

        # Русский комментарий:
        # Это не оптимизация и не подбор стратегии.
        # Это детерминированная атрибуция известных сигналов к уже существующим стратегиям.
        if symbol_text.startswith("BR") or "BR_M5_" in reason_text:
            return StrategyAttributionDecisionV1(
                allowed=True,
                strategy="BR_CONSERVATIVE_BREAKOUT",
                timeframe=timeframe,
                continuous_symbol=continuous_symbol or "BR_CONT",
                reason="STRATEGY_ATTRIBUTED_FROM_BR_SIGNAL",
                source="signal_reason",
                discovery_required=False,
            )

        if symbol_text.startswith("NG") or "NG_" in reason_text:
            return StrategyAttributionDecisionV1(
                allowed=True,
                strategy="NG_CONSERVATIVE_BREAKOUT_M1",
                timeframe=timeframe,
                continuous_symbol=continuous_symbol or "NG_CONT",
                reason="STRATEGY_ATTRIBUTED_FROM_NG_SIGNAL",
                source="signal_reason",
                discovery_required=False,
            )

        if symbol_text.startswith("USDRUB") or "USD" in reason_text or "RUB" in reason_text:
            return StrategyAttributionDecisionV1(
                allowed=True,
                strategy="USDRUB_REGIME",
                timeframe=timeframe,
                continuous_symbol=continuous_symbol or "USDRUB_CONT",
                reason="STRATEGY_ATTRIBUTED_FROM_USDRUB_SIGNAL",
                source="signal_reason",
                discovery_required=False,
            )

        return StrategyAttributionDecisionV1(
            allowed=False,
            strategy=None,
            timeframe=timeframe,
            continuous_symbol=continuous_symbol,
            reason="SIGNAL_REASON_NOT_MAPPED_TO_STRATEGY",
            source="signal_reason",
            discovery_required=True,
        )

    @staticmethod
    def _first_non_empty(*values: Any) -> str | None:
        for value in values:
            if value is None:
                continue

            text = str(value).strip()
            if text:
                return text

        return None

    @staticmethod
    def _default_continuous_symbol(symbol: str) -> str | None:
        s = symbol.upper()

        if s.startswith("BR"):
            return "BR_CONT"

        if s.startswith("NG"):
            return "NG_CONT"

        if s.startswith("USDRUB"):
            return "USDRUB_CONT"

        if s.startswith("GD"):
            return "GOLD_CONT"

        return None
