class RegimeStrategyAdapter:
    """
    Adjusts strategy parameters based on regime.
    Does NOT generate signals.
    """

    def __init__(self, strategy):
        self.strategy = strategy

    def apply(self, regime_state):
        if regime_state.regime == "high":
            self.strategy.risk_multiplier = 0.5
        elif regime_state.regime == "low":
            self.strategy.risk_multiplier = 1.2
        else:
            self.strategy.risk_multiplier = 1.0