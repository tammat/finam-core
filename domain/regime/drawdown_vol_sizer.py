from domain.regime.regime_detector import RegimeState


class DrawdownAdaptiveVolSizer:
    """
    target_vol_eff = base_target_vol * drawdown_factor

    drawdown_factor decreases as portfolio drawdown increases.
    """

    def __init__(
        self,
        base_target_vol: float,
        dd_threshold: float = 0.05,
        min_factor: float = 0.3,
        epsilon: float = 1e-8,
    ):
        self.base_target_vol = float(base_target_vol)
        self.dd_threshold = float(dd_threshold)
        self.min_factor = float(min_factor)
        self.epsilon = epsilon

    def _drawdown_factor(self, portfolio):

        if portfolio is None:
            return 1.0

        # ожидаем, что portfolio имеет realized_pnl и starting_cash
        equity = getattr(portfolio, "equity", None)
        starting = getattr(portfolio, "starting_cash", None)

        if equity is None or starting is None or starting == 0:
            return 1.0

        dd = max(0.0, (starting - equity) / starting)

        if dd <= self.dd_threshold:
            return 1.0

        # линейное снижение после threshold
        excess = dd - self.dd_threshold
        factor = 1.0 - excess

        return max(self.min_factor, factor)

    def apply(self, intent, regime: RegimeState, event=None, portfolio=None):

        if regime.volatility <= self.epsilon:
            return intent

        factor = self._drawdown_factor(portfolio)

        effective_target_vol = self.base_target_vol * factor
        multiplier = effective_target_vol / regime.volatility

        # поддержка Signal
        if hasattr(intent, "quantity"):
            new_qty = intent.quantity * multiplier
            return intent.__class__(
                symbol=intent.symbol,
                side=intent.side,
                quantity=new_qty,
                confidence=getattr(intent, "confidence", 1.0),
                metadata=getattr(intent, "metadata", None),
            )

        if hasattr(intent, "qty"):
            intent.qty = intent.qty * multiplier
            return intent

        return intent