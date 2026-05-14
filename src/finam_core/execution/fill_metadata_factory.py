from __future__ import annotations

from typing import Any


class FillMetadataFactory:
    """Русский комментарий: единый helper metadata для PAPER/REAL/REPLAY fills."""

    @staticmethod
    def build(intent: dict[str, Any] | None, market_state: dict[str, Any] | None = None, raw_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        intent = intent or {}
        market_state = market_state or {}
        raw_payload = raw_payload if isinstance(raw_payload, dict) else {}

        signal_payload = {
            "signal_id": intent.get("signal_id"),
            "strategy": intent.get("strategy") or (intent.get("features") or {}).get("strategy"),
            "horizon": intent.get("horizon") or intent.get("signal_horizon"),
            "regime": intent.get("regime") or market_state.get("regime") or market_state.get("regime_trend"),
            "timeframe": intent.get("timeframe"),
        }

        return {
            **raw_payload,
            **{k: v for k, v in signal_payload.items() if v is not None},
        }

    @staticmethod
    def attach(fill: Any, intent: dict[str, Any] | None, market_state: dict[str, Any] | None = None, raw_fill: Any | None = None) -> Any:
        """Русский комментарий: навешивает signal_id и payload на fill без изменения торговых полей."""
        raw_payload = getattr(raw_fill, "payload", None)
        payload = FillMetadataFactory.build(intent, market_state, raw_payload)

        try:
            fill.signal_id = payload.get("signal_id")
            fill.payload = payload
        except Exception:
            pass

        return fill
