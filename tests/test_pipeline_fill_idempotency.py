# tests/test_pipeline_fill_idempotency.py
import os
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
        # some versions accept done event as last arg
        args.append(done)
    return Pipeline(*args)


def test_fill_idempotency_apply_once(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "src")
    # Ensure pipeline won't exit
    monkeypatch.setenv("EXIT_ON_FILL", "0")

    import scripts.run_market_pipeline as rmp

    bus = EventBus()

    pm = PositionManager(starting_cash=100_000.0)
    # ensure cash initialized for PM (some versions keep it)
    pm.cash = 100_000.0

    portfolio = SimpleNamespace(position_manager=pm)

    # risk not used here
    risk = SimpleNamespace()

    # paper not used here
    paper = SimpleNamespace()

    strategy = SimpleNamespace()

    pipeline = make_pipeline(rmp, bus, portfolio, pm, risk, paper, strategy, done=None)
    pipeline.attach()

    fill = FillEvent(
        fill_id="X",
        symbol="TEST@MISX",
        side="BUY",
        qty=1.0,
        price=10.0,
        commission=0.0,
    )

    # publish same fill twice
    bus.publish({"type": "FILL", "fill": fill, "origin": "paper"})
    bus.publish({"type": "FILL", "fill": fill, "origin": "paper"})

    pos = pm.positions.get("TEST@MISX")
    qty = float(getattr(pos, "qty", 0.0) or 0.0) if pos is not None else 0.0

    assert qty == 1.0, "Fill must be applied once (idempotency)"
