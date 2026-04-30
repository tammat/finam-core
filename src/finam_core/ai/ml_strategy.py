# Комментарии:
# MLStrategy работает параллельно MomentumStrategy.
# Использует FeatureEngine из strategy слоя.
# Публикует SignalEvent независимо.

from datetime import datetime, timezone
from finam_core.storage.postgres import PostgresStorage
from finam_core.core.events import SignalEvent
from finam_core.strategy.feature_engine import FeatureEngine
from finam_core.ai.model_loader import ModelLoader
from finam_core.ai.inference_engine import InferenceEngine


class MLStrategy:

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.features = FeatureEngine(window=10)

        loader = ModelLoader()
        model_info = loader.load_latest()

        self.model_name = "baseline_logreg"
        self.model_version = model_info["version"]

        self.inference = InferenceEngine(
            model=model_info["model"],
            threshold=model_info["threshold"],
            feature_order=model_info["features"],
        )

        self.storage = PostgresStorage()

    
    def on_market(self, event):
        print("MLStrategy received market event")
        self.features.update(event.price)

        if not self.features.ready():
            return

        feature_dict = self.features.compute()

        signal_type, confidence = self.inference.predict(feature_dict)

        # 🔥 ATR (чистая версия)
        try:
            high = float(getattr(event, "high", event.price))
            low = float(getattr(event, "low", event.price))
            close = float(getattr(event, "close", event.price))

            atr = abs(high - low)
            if atr == 0:
                atr = close * 0.005

            feature_dict["atr"] = atr
        except Exception:
            feature_dict["atr"] = float(event.price) * 0.005

        # лог инференса
        self.storage.log_inference(
            model_name=self.model_name,
            model_version=self.model_version,
            symbol=event.symbol,
            timestamp=event.timestamp,
            probability=confidence,
            predicted_label=signal_type,
            features=feature_dict,
        )

        # публикация сигнала
        self.event_bus.publish(
            SignalEvent(
                symbol=event.symbol,
                signal_type=signal_type,
                strength=confidence,
                features=feature_dict,
                timestamp=datetime.now(timezone.utc),
            )
        )

