# core/engine.py
from datetime import datetime, timezone
from core.strategy_manager import StrategyManager


class Engine:

    def __init__(
        self,
        oms,
        position_manager,
        portfolio_manager,
        risk_engine,
        storage,
    ):
        self.oms = oms
        self.position_manager = position_manager
        self.portfolio_manager = portfolio_manager
        self.risk_engine = risk_engine
        self.storage = storage
        self.strategy_manager = StrategyManager()

        self._processed = 0

    # ------------------------------------------------------------
    # ------------------- Main Loop ------------------------------
    # ------------------------------------------------------------

    def run(self):

        for event in self.storage.get_pending_events():

            if event.__class__.__name__ == "MarketEvent":
                self._handle_market(event)

            elif event.__class__.__name__ == "SignalEvent":
                self._handle_signal(event)

            self._processed += 1

        return self._processed

    # ------------------------------------------------------------
    # ------------------- Market Handler -------------------------
    # ------------------------------------------------------------

    def _handle_market(self, event):

        # 1️⃣ Логируем рыночную цену
        self.storage.log_market_price(
            symbol=event.symbol,
            price=event.price,
            volume=getattr(event, "volume", 0.0),
            timestamp=event.timestamp,
        )

        # 2️⃣ Генерируем один агрегированный сигнал (policy="first")
        signal = self.strategy_manager.generate(event, policy="first")

        # Если сигналов нет — выходим
        if signal is None:
            return

        # 3️⃣ Публикуем сигнал в очередь событий (если storage поддерживает),
        # иначе обрабатываем напрямую
        if hasattr(self.storage, "publish_event"):
            self.storage.publish_event(signal)
        else:
            self._handle_signal(signal)

    # ------------------------------------------------------------
    # ------------------- Signal Handler -------------------------
    # -------------------------------------------------------------
    def _handle_signal(self, event):

        # --- Поддержка SignalIntent ---
        if hasattr(event, "direction"):
            order = self.oms.create_order_from_intent(event)
        else:
            order = self.oms.create_order(event)

        market_price = getattr(event, "price", 0.0)
        ts = event.timestamp

        fills = self.oms.process_order(order, market_price, ts)

        for fill in fills:
            self.position_manager.on_fill(fill)
            state = self.portfolio_manager.on_fill(fill)
            self.risk_engine.evaluate(state)

        self.storage.log_signal(event)

        if hasattr(event, "features"):
            self.storage.log_features(
                event_id=getattr(event, "event_id", None),
                features=event.features,
                timestamp=event.timestamp,
            )