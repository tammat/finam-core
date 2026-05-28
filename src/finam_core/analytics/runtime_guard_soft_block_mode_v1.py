from __future__ import annotations

from typing import Any

from finam_core.analytics.runtime_guard_decision_adapter_v1 import (
    RuntimeGuardDecision,
    RuntimeGuardDecisionAdapterV1,
)


class RuntimeGuardSoftBlockModeV1:
    """
    Русский комментарий: soft-block слой НЕ останавливает execution.
    """

    def __init__(self, adapter: RuntimeGuardDecisionAdapterV1 | None = None):
        self.adapter = adapter or RuntimeGuardDecisionAdapterV1()

    @staticmethod
    def _ensure_features(signal: Any) -> dict[str, Any]:
        if isinstance(signal, dict):
            features = signal.get("features")
            if not isinstance(features, dict):
                features = {}
                signal["features"] = features
            return features

        features = getattr(signal, "features", None)
        if not isinstance(features, dict):
            features = {}
            setattr(signal, "features", features)
        return features

    @staticmethod
    def _get_value(signal: Any, key: str, default: Any = None) -> Any:
        if isinstance(signal, dict):
            return signal.get(key, default)
        return getattr(signal, key, default)

    def apply(self, signal: Any) -> RuntimeGuardDecision:
        features = self._ensure_features(signal)

        decision = self.adapter.evaluate(
            symbol=self._get_value(signal, "symbol") or features.get("symbol") or "UNKNOWN",
            strategy=self._get_value(signal, "strategy") or features.get("strategy") or "UNKNOWN",
            timeframe=self._get_value(signal, "timeframe") or features.get("timeframe") or "UNKNOWN",
            regime=features.get("regime"),
            volatility_regime=features.get("volatility_regime"),
            session_type=features.get("session_type"),
        )

        features["runtime_guard_decision"] = decision.decision
        features["runtime_guard_reason"] = decision.reason
        features["runtime_guard_matched"] = decision.matched
        features["runtime_guard_closed_total"] = decision.closed_total
        features["runtime_guard_winrate"] = decision.winrate
        features["runtime_guard_profit_factor"] = decision.profit_factor
        features["runtime_guard_expectancy"] = decision.expectancy
        features["runtime_soft_blocked"] = decision.decision == "BLOCK"

        print(
            "RUNTIME_GUARD_SOFT_BLOCK "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"timeframe={decision.timeframe} "
            f"decision={decision.decision} "
            f"soft_blocked={features['runtime_soft_blocked']} "
            f"matched={decision.matched}",
            flush=True,
        )

        return decision


if __name__ == "__main__":
    runtime = RuntimeGuardSoftBlockModeV1()

    signal = {
        "symbol": "BR_ROLLING@RTSX",
        "strategy": "HISTORICAL_BREAKOUT_V1",
        "timeframe": "M5",
        "features": {
            "regime": "UNKNOWN",
            "volatility_regime": "UNKNOWN",
            "session_type": "UNKNOWN",
        },
    }

    result = runtime.apply(signal)

    print(result)
    print(signal["features"])
