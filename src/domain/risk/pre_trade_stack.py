from domain.risk.risk_decision import RiskDecision


class PreTradeRiskStack:
    def __init__(self, rules):
        self.rules = rules or []

    # основной (для основного пайплайна)
    def evaluate(self, signal, portfolio_state) -> RiskDecision:
        for rule in self.rules:
            decision = rule.evaluate(
                portfolio_state=portfolio_state,
                symbol=signal.symbol,
                side=signal.side,
                qty=signal.qty,
                price=signal.price,
            )
            if not decision.approved:
                return decision
        return RiskDecision.allow()

    # адаптер (для test_risk_limits.py)
    def evaluate_flat(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        equity: float,
        current_exposure: float,
        current_position_notional: float,
        daily_realized_pnl: float,
    ) -> RiskDecision:
        # простой объект "signal"
        signal = type("Signal", (), {})()
        signal.symbol, signal.side, signal.qty, signal.price = symbol, side, qty, price

        # простой объект "portfolio_state"
        ps = type("PortfolioState", (), {})()
        ps.equity = equity
        ps.current_exposure = current_exposure
        ps.current_position_notional = current_position_notional
        ps.daily_realized_pnl = daily_realized_pnl

        return self.evaluate(signal, ps)