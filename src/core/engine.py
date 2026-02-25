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

        # сохраняем цену
        self.storage.log_market_price(
            symbol=event.symbol,
            price=event.price,
            volume=getattr(event, "volume", 0.0),
            timestamp=event.timestamp,
        )

    # ------------------------------------------------------------
    # ------------------- Signal Handler -------------------------
    # ------------------------------------------------------------

    def _handle_signal(self, event):

        # 1️⃣ Создаем ордер
        order = self.oms.create_order(event)

        # 2️⃣ Получаем текущую рыночную цену
        market_price = getattr(event, "price", 0.0)
        ts = event.timestamp

        # 3️⃣ Исполняем (partial fills)
        fills = self.oms.process_order(order, market_price, ts)

        # 4️⃣ Accounting на каждый fill
        for fill in fills:

            self.position_manager.on_fill(fill)

            state = self.portfolio_manager.on_fill(fill)

            # 5️⃣ Risk check после обновления портфеля
            self.risk_engine.evaluate(state)

        # 6️⃣ Логируем сигнал
        self.storage.log_signal(event)

        # 7️⃣ Логируем фичи если есть
        if hasattr(event, "features"):
            self.storage.log_features(
                event_id=event.event_id,
                features=event.features,
                timestamp=event.timestamp,
            )