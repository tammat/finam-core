# tests/test_pipeline_continues_after_fill.py
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
        self.quotes_seen = 0

    def on_quote(self, st: dict):
        self.quotes_seen += 1
        if self.sent:
            return None
        if st.get("symbol") != self.symbol or st.get("last") is None:
            return None
        self.sent = True
        return {"symbol": self.symbol, "side": "BUY", "qty": 1.0}


class PaperStub:
    def execute(self, intent, st):
        return SimpleNamespace(symbol=intent["symbol"], qty=1.0, price=float(st.get("last") or 0.0), commission=0.0, fill_id="paper_1")


class RiskAllow:
    def __init__(self):
        self.stack = SimpleNamespace(evaluate=lambda ctx: SimpleNamespace(allowed=True, reason=None))


def test_quotes_continue_after_fill(monkeypatch):
    monkeypatch.setenv("EXIT_ON_FILL", "0")
    monkeypatch.setenv("RISK_SOFT", "1")  # bypass

    import scripts.run_market_pipeline as rmp

    bus = EventBus()
    pm = PositionManager(starting_cash=100_000.0)
    pm.cash = 100_000.0
    portfolio = SimpleNamespace(position_manager=pm, equity=100_000.0)

    paper = PaperStub()
    risk = RiskAllow()
    strategy = StrategyOnce()

    pipeline = make_pipeline(rmp, bus, portfolio, pm, risk, paper, strategy, done=None)
    pipeline.attach()

    # 1st quote -> triggers fill
    bus.publish({"type": "QUOTE", "symbol": "TEST@MISX", "last": 100.0})
    # more quotes -> must not crash, and strategy must not emit new intents
    bus.publish({"type": "QUOTE", "symbol": "TEST@MISX", "last": 101.0})
    bus.publish({"type": "QUOTE", "symbol": "TEST@MISX", "last": 102.0})

    assert strategy.quotes_seen == 3
    pos = pm.positions.get("TEST@MISX")
    assert float(getattr(pos, "qty", 0.0) or 0.0) == 1.0