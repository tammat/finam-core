# tests/test_pipeline_risk_gate.py
import inspect
from types import SimpleNamespace

import pytest

from finam_core.events.event_bus import EventBus
from finam_core.accounting.position_manager import PositionManager


def make_pipeline(module, bus, portfolio, pm, risk, paper, strategy, done=None):
    Pipeline = module.PaperTradingPipeline
    sig = inspect.signature(Pipeline.__init__)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    args = [bus, portfolio, pm, risk, paper, strategy]
    if len(params) >= 7:
        args.append(done)
    return Pipeline(*args)


class StrategyOnce:
    def __init__(self, symbol="TEST@MISX"):
        self.symbol = symbol
        self.sent = False

    def on_quote(self, st: dict):
        if self.sent:
            return None
        if st.get("symbol") != self.symbol or st.get("last") is None:
            return None
        self.sent = True
        return {"symbol": self.symbol, "side": "BUY", "qty": 1.0}


class PaperSpy:
    def __init__(self):
        self.calls = 0

    def execute(self, intent, st):
        self.calls += 1
        return SimpleNamespace(symbol=intent["symbol"], qty=1.0, price=float(st["last"]), commission=0.0, fill_id="paper_1")


class RiskReject:
    def __init__(self):
        self.stack = SimpleNamespace(evaluate=lambda ctx: SimpleNamespace(allowed=False, reason="deny"))


def test_risk_soft_bypass_allows(monkeypatch):
    monkeypatch.setenv("RISK_SOFT", "1")
    monkeypatch.setenv("EXIT_ON_FILL", "0")

    import scripts.run_market_pipeline as rmp

    bus = EventBus()
    pm = PositionManager(starting_cash=100_000.0)
    pm.cash = 100_000.0
    portfolio = SimpleNamespace(position_manager=pm, equity=100_000.0)

    paper = PaperSpy()
    risk = RiskReject()  # even reject should be bypassed
    strategy = StrategyOnce()

    pipeline = make_pipeline(rmp, bus, portfolio, pm, risk, paper, strategy, done=None)
    pipeline.attach()

    bus.publish({"type": "QUOTE", "symbol": "TEST@MISX", "last": 100.0})
    assert paper.calls == 1


def test_risk_hard_reject_blocks(monkeypatch):
    monkeypatch.setenv("RISK_SOFT", "0")
    monkeypatch.setenv("EXIT_ON_FILL", "0")

    import scripts.run_market_pipeline as rmp

    bus = EventBus()
    pm = PositionManager(starting_cash=100_000.0)
    pm.cash = 100_000.0
    portfolio = SimpleNamespace(position_manager=pm, equity=100_000.0)

    paper = PaperSpy()
    risk = RiskReject()
    strategy = StrategyOnce()

    pipeline = make_pipeline(rmp, bus, portfolio, pm, risk, paper, strategy, done=None)
    pipeline.attach()

    bus.publish({"type": "QUOTE", "symbol": "TEST@MISX", "last": 100.0})
    assert paper.calls == 0, "paper.execute must not be called when risk rejects"