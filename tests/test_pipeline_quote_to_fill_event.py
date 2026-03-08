# tests/test_pipeline_quote_to_fill_event.py
import inspect
from types import SimpleNamespace

import pytest

from finam_core.events.event_bus import EventBus
from finam_core.accounting.position_manager import PositionManager
from finam_core.core.events.fill_event import FillEvent


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
        if st.get("symbol") != self.symbol:
            return None
        if st.get("last") is None:
            return None
        self.sent = True
        return {"symbol": self.symbol, "side": "BUY", "qty": 1.0}


class PaperStub:
    def execute(self, intent, st):
        # minimal "PaperFill-like" object
        return SimpleNamespace(
            symbol=intent["symbol"],
            qty=1.0,
            price=float(st.get("last") or 0.0),
            commission=0.0,
            fill_id="paper_TEST_1",
        )


class RiskAllow:
    def __init__(self):
        self.stack = SimpleNamespace(evaluate=lambda ctx: SimpleNamespace(allowed=True, reason=None))


def test_quote_emits_fill_event(monkeypatch):
    monkeypatch.setenv("EXIT_ON_FILL", "0")
    monkeypatch.setenv("RISK_SOFT", "0")

    import scripts.run_market_pipeline as rmp

    bus = EventBus()

    pm = PositionManager(starting_cash=100_000.0)
    pm.cash = 100_000.0

    portfolio = SimpleNamespace(position_manager=pm, mark_price=lambda s, p: None, equity=100_000.0)

    risk = RiskAllow()
    paper = PaperStub()
    strategy = StrategyOnce("TEST@MISX")

    # capture fills
    got = []

    def on_fill(ev):
        got.append(ev)

    bus.subscribe("FILL", on_fill)

    pipeline = make_pipeline(rmp, bus, portfolio, pm, risk, paper, strategy, done=None)
    pipeline.attach()

    # publish QUOTE
    bus.publish({"type": "QUOTE", "symbol": "TEST@MISX", "last": 100.0, "bid": 99.0, "ask": 101.0, "volume": 0.0})

    assert len(got) == 1
    assert got[0]["type"] == "FILL"
    assert isinstance(got[0]["fill"], FillEvent)
    assert got[0]["fill"].symbol == "TEST@MISX"
    assert got[0]["fill"].side == "BUY"
    assert got[0]["fill"].qty == 1.0