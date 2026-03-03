from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskDecision:
    approved: bool
    reason: Optional[str] = None


class PreTradeRiskEngine:

    def __init__(self, config):
        self.config = config

        self.max_risk_per_trade_pct = config.max_risk_per_trade
        self.max_total_exposure = config.max_total_exposure
        self.max_position_per_symbol = config.max_position_per_symbol
        self.daily_loss_limit = config.daily_loss_limit
        self.allowed_symbols = config.allowed_symbols
        self.trading_enabled = config.trading_enabled

    def evaluate(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        equity: float,
        current_exposure: float,
        current_position_notional: float,
        daily_realized_pnl: float,
    ):
        if not self.trading_enabled:
            return RiskDecision(False, "trading_disabled")

        if symbol not in self.allowed_symbols:
            return RiskDecision(False, "symbol_not_allowed")

        notional = qty * price

        # 1️⃣ TOTAL EXPOSURE
        if (current_exposure + notional) > self.max_total_exposure:
            return RiskDecision(False, "max_total_exposure_exceeded")

        # 2️⃣ POSITION PER SYMBOL
        if (current_position_notional + notional) > self.max_position_per_symbol:
            return RiskDecision(False, "max_position_per_symbol_exceeded")

        # 3️⃣ RISK PER TRADE
        if equity > 0 and (notional / equity) > self.max_risk_per_trade_pct:
            return RiskDecision(False, "max_risk_per_trade_exceeded")

        # 4️⃣ DAILY LOSS
        if daily_realized_pnl <= -abs(self.daily_loss_limit):
            return RiskDecision(False, "daily_loss_limit_exceeded")

        return RiskDecision(True, None)