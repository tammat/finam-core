from dataclasses import dataclass
from core.events import OrderEvent, RiskRejectedEvent


@dataclass
class RiskConfig:
    max_risk_per_trade: float = 0.02
    daily_loss_limit: float = 0.05
    exposure_limit: float = 0.30
    kill_switch: bool = False


class RiskEngine:
    """
    Centralized institutional risk engine.
    Now equity-aware.
    """

    def __init__(self, portfolio, event_bus, price_resolver, config=None):
        self.portfolio = portfolio
        self.event_bus = event_bus
        self.config = config or RiskConfig()
        self.daily_pnl = 0.0  # placeholder for v1.2+
        self.price_resolver = price_resolver

    def on_signal(self, signal):
        # 1️⃣ Kill switch
        if self.config.kill_switch:
            self._reject(signal, "KILL_SWITCH")
            return

        # 2️⃣ Daily loss control (placeholder logic)
        if self.daily_pnl < -abs(self.config.daily_loss_limit):
            self._reject(signal, "DAILY_LOSS_LIMIT")
            return

        # 3️⃣ Exposure control
        if self.portfolio.total_exposure_fraction() > self.config.exposure_limit:
            self._reject(signal, "EXPOSURE_LIMIT")
            return

        # 4️⃣ Equity-aware sizing (v1.1 simplified)
        equity = self.portfolio.current_equity(self.price_resolver)
        max_capital_at_risk = equity * self.config.max_risk_per_trade

        qty = self.portfolio.calculate_position_size(signal)

        if qty <= 0:
            self._reject(signal, "ZERO_QTY")
            return

        side = "BUY" if signal.signal_type == "LONG" else "SELL"

        self.event_bus.publish(
            OrderEvent(
                symbol=signal.symbol,
                side=side,
                quantity=qty,
                timestamp=signal.timestamp,
                meta={
                    "risk_checked": True,
                    "equity": equity,
                    "max_capital_at_risk": max_capital_at_risk,
                }
            )
        )

    def _reject(self, signal, reason):
        self.event_bus.publish(
            RiskRejectedEvent(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                reason=reason,
                timestamp=signal.timestamp,
                meta={}
            )
        )