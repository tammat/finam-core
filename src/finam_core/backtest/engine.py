from dataclasses import dataclass
from typing import Iterable
from datetime import datetime

from finam_core.accounting.portfolio_manager import PortfolioManager


@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class BacktestEngine:

    def __init__(self, strategy, risk_engine, initial_cash: float = 1_000_000):
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.portfolio = PortfolioManager(initial_cash=initial_cash)
        self.equity_curve = []

    def run(self, bars: Iterable[Bar]):

        for bar in bars:

            # --- STATE SNAPSHOT ---
            state = self.portfolio.compute_state()

            # --- STRATEGY ---
            signal = self.strategy.on_bar(bar, state.equity)

            if signal:
                decision = self.risk_engine.evaluate(signal, state)

                if decision.approved:
                    fill = signal.to_fill(price=bar.close)
                    self.portfolio.on_fill(fill)

            # --- MARK TO MARKET ---
            # Предполагаем single-symbol backtest
            for symbol in self.portfolio.position_manager.positions.keys():
                self.portfolio.mark_price(symbol, bar.close)

            # --- FINAL STATE AFTER BAR ---
            final_state = self.portfolio.compute_state()

            self.equity_curve.append(
                (bar.timestamp, final_state.equity)
            )

        return self.equity_curve