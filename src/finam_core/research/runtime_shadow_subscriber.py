from typing import Any

from finam_core.research.events import MarketFeaturesReadyEvent


class RuntimeShadowSubscriber:
    # Shadow subscriber получает только копию runtime-события.
    # Ничего не меняет в Runtime и Execution.

    def market_data_to_features_event(self, event: dict[str, Any]) -> MarketFeaturesReadyEvent:
        features = dict(event.get("features", {}))

        for key in ("close", "trend", "volatility", "session"):
            if key in event and key not in features:
                features[key] = event[key]

        return MarketFeaturesReadyEvent(
            symbol=str(event.get("symbol", "UNKNOWN")),
            timeframe=str(event.get("timeframe", "UNKNOWN")),
            features=features,
        )
