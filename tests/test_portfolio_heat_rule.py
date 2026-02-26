from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig


class DummyPosition:
    def __init__(self, qty, price):
        self.quantity = qty
        self.avg_price = price
        self.mark_price = price


class DummyPortfolio:
    def __init__(self):
        self.positions = {}
        self.equity = 1000
        self.exposure = 0
        self.cash = 1000
        self.realized_pnl = 0

    def get_exposure(self, symbol):
        return 0


# -------------------------
# TEST 1: Heat blocks
# -------------------------
def test_portfolio_heat_blocks_when_exceeded():
    config = RiskConfig(
        max_risk_per_trade=10_000,
        max_total_exposure=10_000,
        daily_loss_limit=10_000,
        max_portfolio_heat=1.0,
    )

    engine = PreTradeRiskEngine(config)

    portfolio = DummyPortfolio()
    portfolio.positions["SI"] = DummyPosition(qty=15, price=100)  # exposure=1500

    allowed, reason = engine.validate(
        portfolio_state=portfolio,
        symbol="SI",
        side="BUY",
        qty=1,
        price=100,
    )

    assert allowed is False
    assert reason == "MAX_PORTFOLIO_HEAT_EXCEEDED"


# -------------------------
# TEST 2: Heat allows
# -------------------------
def test_portfolio_heat_allows_when_within_limit():
    config = RiskConfig(
        max_risk_per_trade=10_000,
        max_total_exposure=10_000,
        daily_loss_limit=10_000,
        max_portfolio_heat=2.0,
    )

    engine = PreTradeRiskEngine(config)

    portfolio = DummyPortfolio()
    portfolio.positions["SI"] = DummyPosition(qty=10, price=100)  # exposure=1000

    allowed, reason = engine.validate(
        portfolio_state=portfolio,
        symbol="SI",
        side="BUY",
        qty=1,
        price=100,
    )

    assert allowed is True
    assert reason is None