from datetime import datetime, timezone

from core.events import SignalEvent
from strategy.feature_engine import FeatureEngine


class MomentumStrategy:
    """
    Simple momentum strategy using FeatureEngine.
    Generates LONG / SHORT signals based on z-score.
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.features = FeatureEngine(window=10)

    # ----------------------------------------
    # MARKET EVENT HANDLER
    # ----------------------------------------

    def on_market(self, event):

        # 1️⃣ обновляем rolling окно
        self.features.update(event.price)

        # 2️⃣ проверяем готовность
        if not self.features.ready():
            return

        feature_dict = self.features.compute()

        if feature_dict is None:
            return

        # 3️⃣ Простая логика сигнала
        z = feature_dict["z_score"]

        signal_type = None

        if z > 1.5:
            signal_type = "SHORT"
        elif z < -1.5:
            signal_type = "LONG"

        if not signal_type:
            return

        # 4️⃣ Публикуем сигнал
        self.event_bus.publish(
            SignalEvent(
                symbol=event.symbol,
                signal_type=signal_type,
                strength=abs(z),
                features=feature_dict,
                timestamp=datetime.now(timezone.utc),
            )
        )