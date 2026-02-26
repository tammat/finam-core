from dataclasses import dataclass
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Deque

@dataclass
class RiskConfig:
    max_risk_per_trade: float
    max_total_exposure: float
    daily_loss_limit: float
    max_portfolio_heat: float

@dataclass
class LatencySample:
    ts_ns: int
    latency_ns: int
    where: str
    symbol: str

class LatencyRecorder:
    """
    Minimal recorder: keeps last N samples + rolling stats.
    Safe for prod (bounded memory), no external deps.
    """
    def __init__(self, maxlen: int = 10_000):
        self.samples: Deque[LatencySample] = deque(maxlen=maxlen)
        self.count = 0
        self.sum_ns = 0
        self.max_ns = 0

    def record(self, where: str, symbol: str, latency_ns: int):
        self.count += 1
        self.sum_ns += latency_ns
        if latency_ns > self.max_ns:
            self.max_ns = latency_ns
        self.samples.append(LatencySample(
            ts_ns=time.time_ns(),
            latency_ns=latency_ns,
            where=where,
            symbol=symbol,
        ))

    def mean_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return (self.sum_ns / self.count) / 1_000_000.0

    def max_ms(self) -> float:
        return self.max_ns / 1_000_000.0

class PreTradeRiskEngine:

    def __init__(self, config: RiskConfig):
        self.config = config
        self.kill_switch = False
        self.correlation_groups = {
            "ENERGY": {"NG", "BR"},
            "FX_ENERGY": {"NG", "BR", "USDRUB"},
        }
        self.latency: Optional[LatencyRecorder] = None
        if os.getenv("RISK_LATENCY", "0") == "1":
            self.latency = LatencyRecorder(maxlen=int(os.getenv("RISK_LATENCY_MAXLEN", "10000")))
        self.max_group_exposure = 200_000  # example limit
    def enable_kill_switch(self):
        self.kill_switch = True

    def disable_kill_switch(self):
        self.kill_switch = False

    def validate(self, portfolio_state, symbol: str, side: str, qty: float, price: float):
        """
        Returns: (allowed: bool, reason: str | None)
        """
        t0 = time.perf_counter_ns() if self.latency else None

        try:
            if self.kill_switch:
                return False, "KILL_SWITCH_ACTIVE"

            trade_value = qty * price

            # ---- RULE 1.5: Correlated exposure ----
            ok, reason = self._check_correlation_exposure(
                portfolio_state,
                symbol,
                trade_value,
            )
            if not ok:
                return False, reason

            # ---- RULE 1.8: Portfolio Heat ----
            gross_exposure = self._calculate_gross_exposure(portfolio_state)

            equity = getattr(portfolio_state, "equity", None)
            if equity and equity > 0:
                # heat должен считаться по ПРОГНОЗНОЙ экспозиции, включая новую сделку
                projected_gross = gross_exposure + abs(trade_value)
                heat = projected_gross / equity
                if heat > self.config.max_portfolio_heat:
                    return False, "MAX_PORTFOLIO_HEAT_EXCEEDED"
            # ---- RULE 1: Max risk per trade ----
            if trade_value > self.config.max_risk_per_trade:
                return False, "MAX_RISK_PER_TRADE_EXCEEDED"

            # ---- PROJECTED STATE ----
            current_exposure = gross_exposure
            projected_exposure = current_exposure + trade_value
            if projected_exposure > self.config.max_total_exposure:
                return False, "MAX_TOTAL_EXPOSURE_EXCEEDED"

            # ---- PROJECTED CASH (только если атрибут реально есть) ----
            if hasattr(portfolio_state, "cash"):
                cash = getattr(portfolio_state, "cash", None)
                if cash is not None:
                    if side.upper() == "BUY":
                        projected_cash = cash - trade_value
                    else:
                        projected_cash = cash + trade_value
                    if projected_cash < 0:
                        return False, "INSUFFICIENT_CASH"

            return True, None

        finally:
            if self.latency and t0 is not None:
                dt = time.perf_counter_ns() - t0
                self.latency.record(where="risk.validate", symbol=symbol, latency_ns=dt)
    def _check_correlation_exposure(self, portfolio_state, symbol, new_notional):
        for group_name, symbols in self.correlation_groups.items():
            if symbol in symbols:

                current = 0.0

                if hasattr(portfolio_state, "positions"):
                    for s in symbols:
                        pos = portfolio_state.positions.get(s)
                        if pos:
                            quantity = getattr(pos, "qty", getattr(pos, "quantity", 0.0))
                            mark_price = getattr(
                                pos,
                                "mark_price",
                                getattr(pos, "price", getattr(pos, "avg_price", 0.0)),
                            )
                            current += abs(quantity * mark_price)

                elif hasattr(portfolio_state, "exposure"):
                    current = abs(portfolio_state.exposure)

                if current + new_notional > self.max_group_exposure:
                    return False, "CORRELATED_EXPOSURE_EXCEEDED"

        return True, None

    def _calculate_gross_exposure(self, portfolio_state):
        gross = 0.0

        if hasattr(portfolio_state, "positions"):
            for pos in portfolio_state.positions.values():
                quantity = getattr(pos, "qty", getattr(pos, "quantity", 0.0))

                mark_price = getattr(
                    pos,
                    "mark_price",
                    getattr(pos, "price", getattr(pos, "avg_price", 0.0)),
                )

                gross += abs(quantity * mark_price)

        elif hasattr(portfolio_state, "exposure"):
            gross = abs(portfolio_state.exposure)

        return gross
