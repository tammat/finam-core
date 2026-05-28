from __future__ import annotations

from typing import Any

from finam_core.analytics.runtime_guard_decision_adapter_v1 import (
    RuntimeGuardDecision,
    RuntimeGuardDecisionAdapterV1,
)


class RuntimeGuardObservabilityHookV1:
    """
    Русский комментарий:
    Observability hook для runtime guard.
    Не блокирует исполнение.
    Не меняет risk/execution/OMS.
    Только формирует структурированную telemetry-строку.
    """

    def __init__(
        self,
        adapter: RuntimeGuardDecisionAdapterV1 | None = None,
    ):
        self.adapter = adapter or RuntimeGuardDecisionAdapterV1()

    @staticmethod
    def _get_signal_value(signal: Any, key: str, default: Any = None) -> Any:
        if isinstance(signal, dict):
            return signal.get(key, default)

        return getattr(signal, key, default)

    @staticmethod
    def _extract_features(signal: Any) -> dict[str, Any]:
        if isinstance(signal, dict):
            features = signal.get("features")
        else:
            features = getattr(signal, "features", None)

        return features if isinstance(features, dict) else {}

    def observe_signal(self, signal: Any) -> RuntimeGuardDecision:
        features = self._extract_features(signal)

        symbol = (
            self._get_signal_value(signal, "symbol")
            or features.get("symbol")
            or "UNKNOWN"
        )

        strategy = (
            self._get_signal_value(signal, "strategy")
            or features.get("strategy")
            or self._get_signal_value(signal, "strategy_name")
            or features.get("strategy_name")
            or "UNKNOWN"
        )

        timeframe = (
            self._get_signal_value(signal, "timeframe")
            or features.get("timeframe")
            or "UNKNOWN"
        )

        regime = (
            self._get_signal_value(signal, "regime")
            or features.get("regime")
            or features.get("regime_label")
            or "UNKNOWN"
        )

        volatility_regime = (
            self._get_signal_value(signal, "volatility_regime")
            or features.get("volatility_regime")
            or "UNKNOWN"
        )

        session_type = (
            self._get_signal_value(signal, "session_type")
            or features.get("session_type")
            or "UNKNOWN"
        )

        decision = self.adapter.evaluate(
            symbol=str(symbol),
            strategy=str(strategy),
            timeframe=str(timeframe),
            regime=str(regime),
            volatility_regime=str(volatility_regime),
            session_type=str(session_type),
        )

        print(
            "RUNTIME_GUARD_OBSERVABILITY "
            f"symbol={decision.symbol} "
            f"strategy={decision.strategy} "
            f"timeframe={decision.timeframe} "
            f"regime={decision.regime} "
            f"volatility_regime={decision.volatility_regime} "
            f"session_type={decision.session_type} "
            f"decision={decision.decision} "
            f"matched={decision.matched} "
            f"reason={decision.reason}",
            flush=True,
        )

        return decision


if __name__ == "__main__":
    hook = RuntimeGuardObservabilityHookV1()

    decision = hook.observe_signal({
        "symbol": "BR_ROLLING@RTSX",
        "strategy": "HISTORICAL_BREAKOUT_V1",
        "timeframe": "M5",
        "features": {
            "regime": "UNKNOWN",
            "volatility_regime": "UNKNOWN",
            "session_type": "UNKNOWN",
        },
    })

    print(decision)
