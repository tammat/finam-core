from dataclasses import dataclass


@dataclass
class RiskConfig:
    max_risk_per_trade: float
    max_total_exposure: float
    daily_loss_limit: float


class PreTradeRiskEngine:

    def __init__(self, config: RiskConfig):
        self.config = config
        self.kill_switch = False

    def enable_kill_switch(self):
        self.kill_switch = True

    def disable_kill_switch(self):
        self.kill_switch = False

    def validate(self, portfolio_state, side: str, qty: float, price: float):
        """
        Returns: (allowed: bool, reason: str | None)
        """

        if self.kill_switch:
            return False, "KILL_SWITCH_ACTIVE"

        trade_value = qty * price

        # ---- RULE 1: Max risk per trade ----
        if trade_value > self.config.max_risk_per_trade:
            return False, "MAX_RISK_PER_TRADE_EXCEEDED"

        # ---- PROJECTED STATE ----
        projected_exposure = portfolio_state.exposure + trade_value

        if projected_exposure > self.config.max_total_exposure:
            return False, "MAX_TOTAL_EXPOSURE_EXCEEDED"

        # ---- PROJECTED CASH ----
        if side.upper() == "BUY":
            projected_cash = portfolio_state.cash - trade_value
        else:
            projected_cash = portfolio_state.cash + trade_value

        if projected_cash < 0:
            return False, "NEGATIVE_CASH"

        # ---- DAILY LOSS LIMIT ----
        if portfolio_state.realized_pnl < -self.config.daily_loss_limit:
            return False, "DAILY_LOSS_LIMIT_EXCEEDED"

        return True, None
