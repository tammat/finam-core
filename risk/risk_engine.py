from dataclasses import dataclass


@dataclass
class RiskState:
    exposure: float
    drawdown: float
    equity: float


class RiskEngine:
    """
    Production v1 Risk Engine.
    Контролирует drawdown и возвращает состояние риска.
    """

    def __init__(self, position_manager=None, portfolio_manager=None, max_drawdown: float = 0.3):
        self.position_manager = position_manager
        self.portfolio_manager = portfolio_manager
        self.max_drawdown = max_drawdown
        self.peak_equity = None

    # ====================================================
    # ENTRY POINT (вызывается из Engine)
    # ====================================================

    def evaluate(self, portfolio_state) -> RiskState:
        equity = portfolio_state.equity

        if self.peak_equity is None:
            self.peak_equity = equity

        if equity > self.peak_equity:
            self.peak_equity = equity

        drawdown = 0.0
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - equity) / self.peak_equity

        if drawdown > self.max_drawdown:
            raise RuntimeError(
                f"Max drawdown exceeded: {drawdown:.2%} > {self.max_drawdown:.2%}"
            )

        return RiskState(
            exposure=portfolio_state.exposure,
            drawdown=drawdown,
            equity=equity,
        )