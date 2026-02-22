from dataclasses import dataclass
from typing import List
from risk.models import RiskDecision


@dataclass
class RiskContext:
    symbol: str
    side: str
    qty: float
    price: float
    current_position_qty: float
    current_portfolio_exposure: float
    current_drawdown: float


class RiskRule:
    def evaluate(self, ctx: RiskContext) -> RiskDecision:
        raise NotImplementedError


# ======================================================
# RULES
# ======================================================

class MaxPositionSizeRule(RiskRule):

    def __init__(self, max_qty: float):
        self.max_qty = max_qty

    def evaluate(self, ctx: RiskContext):

        signed = ctx.qty if ctx.side == "BUY" else -ctx.qty
        projected = ctx.current_position_qty + signed

        if abs(projected) > self.max_qty:
            return RiskDecision(False, "MaxPositionSize", "Position size exceeded")

        return RiskDecision(True)


class MaxPortfolioExposureRule(RiskRule):

    def __init__(self, max_exposure: float):
        self.max_exposure = max_exposure

    def evaluate(self, ctx: RiskContext):

        projected_exposure = ctx.current_portfolio_exposure + abs(ctx.qty * ctx.price)

        if projected_exposure > self.max_exposure:
            return RiskDecision(False, "MaxPortfolioExposure", "Exposure limit exceeded")

        return RiskDecision(True)


class MaxDrawdownRule(RiskRule):

    def __init__(self, max_drawdown: float):
        self.max_drawdown = max_drawdown

    def evaluate(self, ctx: RiskContext):

        if ctx.current_drawdown > self.max_drawdown:
            return RiskDecision(False, "MaxDrawdown", "Drawdown limit breached")

        return RiskDecision(True)


# ======================================================
# ENGINE
# ======================================================

class RiskEngine:

    def __init__(
        self,
        position_manager,
        portfolio_manager,
        max_position_size=10,
        max_exposure=1_000_000,
        max_drawdown=50_000,
    ):
        self.position_manager = position_manager
        self.portfolio_manager = portfolio_manager

        self.rules: List[RiskRule] = [
            MaxPositionSizeRule(max_position_size),
            MaxPortfolioExposureRule(max_exposure),
            MaxDrawdownRule(max_drawdown),
        ]

    # --------------------------------------------------
    # PRE-TRADE CHECK
    # --------------------------------------------------

    def pre_trade_check(self, symbol: str, side: str, qty: float, price: float, timestamp):

        position = self.position_manager.get(symbol)
        portfolio_state = self.portfolio_manager.compute_state(
            self.position_manager,
            timestamp,
        )

        ctx = RiskContext(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            current_position_qty=position.qty,
            current_portfolio_exposure=self.position_manager.total_exposure(),
            current_drawdown=portfolio_state.drawdown,
        )

        for rule in self.rules:
            decision = rule.evaluate(ctx)
            if not decision.allowed:
                return decision

        return RiskDecision(True)