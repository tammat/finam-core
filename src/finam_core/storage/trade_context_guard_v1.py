from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.runtime.research_contract_key_v1 import normalize_research_contract_key_v1


# Русский комментарий:
# TradeContextGuardV1 — обязательный guard перед записью trades.
# Его задача: не допустить пустые strategy/timeframe/continuous_symbol
# для известных runtime маршрутов. AI слой не имеет права обходить этот guard.


@dataclass(frozen=True)
class TradeContextDecisionV1:
    allowed: bool
    strategy: str
    timeframe: str
    continuous_symbol: str
    reason: str


class TradeContextGuardV1:
    KNOWN_ROUTES: dict[str, tuple[str, str, str]] = {
        "USDRUBF@RTSX": ("USDRUB_REGIME", "LIVE", "USDRUB_CONT"),
        "NGM6@RTSX": ("NG_CONSERVATIVE_BREAKOUT_M1", "LIVE", "NG_CONT"),
        "NGN6@RTSX": ("NG_CONSERVATIVE_BREAKOUT_M1", "LIVE", "NG_CONT"),
        "BRN6@RTSX": ("BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT"),
        "BRQ6@RTSX": ("BR_CONSERVATIVE_BREAKOUT", "M5", "BR_CONT"),
    }

    def normalize(
        self,
        *,
        symbol: str,
        strategy: str | None,
        timeframe: str | None,
        continuous_symbol: str | None,
        payload: dict[str, Any] | None = None,
    ) -> TradeContextDecisionV1:
        symbol = str(symbol or "").strip()
        strategy = str(strategy or "").strip()
        timeframe = str(timeframe or "").strip()
        continuous_symbol = str(continuous_symbol or "").strip()
        payload = payload or {}

        if strategy and strategy not in {"UNKNOWN", "UNKNOWN_STRATEGY"}:
            if timeframe and timeframe not in {"UNKNOWN", "UNKNOWN_TIMEFRAME"}:
                if continuous_symbol:
                    key = normalize_research_contract_key_v1(
                        symbol=symbol,strategy=strategy,timeframe=timeframe,side="UNKNOWN",
                        session_name="UNKNOWN",regime="UNKNOWN",
                    )
                    return TradeContextDecisionV1(
                        allowed=True,
                        strategy=key.strategy,
                        timeframe=key.timeframe,
                        continuous_symbol=key.normalized_symbol,
                        reason="context_canonicalized",
                    )

        payload_strategy, payload_timeframe, payload_continuous = self._from_payload(payload)

        if not strategy or strategy in {"UNKNOWN", "UNKNOWN_STRATEGY"}:
            strategy = payload_strategy or strategy

        if not timeframe or timeframe in {"UNKNOWN", "UNKNOWN_TIMEFRAME"}:
            timeframe = payload_timeframe or timeframe

        if not continuous_symbol:
            continuous_symbol = payload_continuous or continuous_symbol

        if strategy and timeframe and continuous_symbol:
            if strategy not in {"UNKNOWN", "UNKNOWN_STRATEGY"} and timeframe not in {"UNKNOWN", "UNKNOWN_TIMEFRAME"}:
                key = normalize_research_contract_key_v1(
                    symbol=symbol,strategy=strategy,timeframe=timeframe,side="UNKNOWN",
                    session_name="UNKNOWN",regime="UNKNOWN",
                )
                return TradeContextDecisionV1(
                    allowed=True,
                    strategy=key.strategy,
                    timeframe=key.timeframe,
                    continuous_symbol=key.normalized_symbol,
                    reason="context_restored_from_payload",
                )

        if symbol in self.KNOWN_ROUTES:
            fallback_strategy, fallback_timeframe, fallback_continuous = self.KNOWN_ROUTES[symbol]
            return TradeContextDecisionV1(
                allowed=True,
                strategy=fallback_strategy,
                timeframe=fallback_timeframe,
                continuous_symbol=continuous_symbol or fallback_continuous,
                reason="context_restored_from_known_route",
            )

        return TradeContextDecisionV1(
            allowed=False,
            strategy=strategy or "UNKNOWN",
            timeframe=timeframe or "UNKNOWN",
            continuous_symbol=continuous_symbol or symbol or "UNKNOWN",
            reason="trade_context_missing_unknown_route",
        )

    def _from_payload(self, payload: dict[str, Any]) -> tuple[str, str, str]:
        candidates: list[dict[str, Any]] = []

        if isinstance(payload, dict):
            candidates.append(payload)

        for key in (
            "trade_context_snapshot",
            "trade_context",
            "risk_context",
            "signal",
            "raw",
            "payload",
        ):
            value = payload.get(key) if isinstance(payload, dict) else None
            if isinstance(value, dict):
                candidates.append(value)

        for item in candidates:
            strategy = str(item.get("strategy") or item.get("strategy_name") or "").strip()
            timeframe = str(item.get("timeframe") or item.get("tf") or "").strip()
            continuous_symbol = str(
                item.get("continuous_symbol") or item.get("continuous") or ""
            ).strip()

            if strategy or timeframe or continuous_symbol:
                return strategy, timeframe, continuous_symbol

        return "", "", ""
