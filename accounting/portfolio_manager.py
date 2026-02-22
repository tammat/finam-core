from dataclasses import dataclass


@dataclass
class PortfolioState:
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    exposure: float
    drawdown: float


class PortfolioManager:
    """
    Production v1 portfolio manager.
    Tracks cash, equity and drawdown.
    """

    def __init__(self, initial_cash: float = 100000.0):
        self.cash = float(initial_cash)
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.exposure = 0.0

        self._equity_peak = float(initial_cash)
        self.drawdown = 0.0

    # ====================================================
    # FILL HANDLING
    # ====================================================

    def on_fill(self, fill) -> PortfolioState:
        side = fill.side.upper()
        notional = fill.qty * fill.price
        commission = getattr(fill, "commission", 0.0)

        if side == "BUY":
            self.cash -= notional
        else:
            self.cash += notional

        self.cash -= commission
        self.realized_pnl -= commission

        equity = self.cash + self.unrealized_pnl

        # ---- drawdown logic ----
        if equity > self._equity_peak:
            self._equity_peak = equity

        if self._equity_peak > 0:
            self.drawdown = (self._equity_peak - equity) / self._equity_peak
        else:
            self.drawdown = 0.0

        return PortfolioState(
            cash=self.cash,
            equity=equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            exposure=self.exposure,
            drawdown=self.drawdown,
        )

    # ====================================================
    # STATE COMPUTATION
    # ====================================================

    def compute_state(self, position_manager, now_ts) -> PortfolioState:
        positions = getattr(position_manager, "positions", {}) or {}

        equity = self.cash
        exposure = 0.0

        for symbol, pos in positions.items():
            qty = getattr(pos, "qty", 0.0)
            price = getattr(pos, "price", 0.0)

            notional = qty * price
            equity += notional
            exposure += abs(notional)

        # ---- drawdown calculation ----
        if equity > self._equity_peak:
            self._equity_peak = equity

        if self._equity_peak > 0:
            drawdown = (self._equity_peak - equity) / self._equity_peak
        else:
            drawdown = 0.0

        return PortfolioState(
            cash=float(self.cash),
            equity=float(equity),
            realized_pnl=float(self.realized_pnl),
            unrealized_pnl=float(self.unrealized_pnl),
            exposure=float(exposure),
            drawdown=float(drawdown),
        )