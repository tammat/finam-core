from __future__ import annotations

from typing import Any

from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver


class FillMetadataFactory:
    """Русский комментарий: единый helper metadata для PAPER/REAL/REPLAY fills."""

    @staticmethod
    def build(intent: dict[str, Any] | None, market_state: dict[str, Any] | None = None, raw_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        intent = intent or {}
        market_state = market_state or {}
        raw_payload = raw_payload if isinstance(raw_payload, dict) else {}

        symbol = (
            intent.get("symbol")
            or market_state.get("symbol")
            or raw_payload.get("symbol")
            or ""
        )
        identity = ContractIdentityResolver.resolve(str(symbol))

        features = intent.get("features") or {}

        regime_label = (
            intent.get("regime")
            or features.get("regime_label")
            or market_state.get("regime")
            or market_state.get("regime_label")
            or market_state.get("regime_trend")
        )

        signal_payload = {
            "signal_id": intent.get("signal_id"),
            "strategy": intent.get("strategy") or features.get("strategy"),
            "horizon": intent.get("horizon") or intent.get("signal_horizon"),
            "regime": regime_label,
            "regime_label": regime_label,
            "confidence": intent.get("confidence") or features.get("confidence"),
            "timeframe": intent.get("timeframe"),
            "root_symbol": identity.root,
            "continuous_symbol": identity.continuous if identity.is_futures else identity.symbol,
            "futures_month_code": identity.month_code,
            "futures_year_code": identity.year_code,
            "is_futures": identity.is_futures,
            "venue": identity.venue,
            "regime_source_version": features.get("regime_source_version"),
            "regime_timeframe": features.get("regime_timeframe") or intent.get("timeframe"),
            "regime_bar_ts": features.get("regime_bar_ts"),
            "regime_atr": features.get("regime_atr"),
            "regime_atr_pct": features.get("regime_atr_pct"),
            "regime_atr_percentile": features.get("regime_atr_percentile"),
            "regime_adx": features.get("regime_adx"),
            "regime_normalized_slope": features.get("regime_normalized_slope"),
            "regime_confirmed_bars": features.get("regime_confirmed_bars"),
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
