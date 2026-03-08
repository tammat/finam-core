# tests/test_fill_event_mapping.py
from types import SimpleNamespace

import pytest

from finam_core.core.events.fill_event import FillEvent


def test_fill_event_fields():
    # "PaperFill-like"
    paper_fill = SimpleNamespace(
        symbol="TEST@MISX",
        qty=1.0,
        price=10.0,
        commission=0.1,
        fill_id="paper_TEST_1",
    )

    side = "BUY"
    qty = abs(float(paper_fill.qty))

    ev = FillEvent(
        fill_id=getattr(paper_fill, "fill_id", None),
        symbol=getattr(paper_fill, "symbol", None),
        side=side,
        qty=qty,
        price=float(getattr(paper_fill, "price", 0.0) or 0.0),
        commission=float(getattr(paper_fill, "commission", 0.0) or 0.0),
    )

    assert ev.fill_id == "paper_TEST_1"
    assert ev.symbol == "TEST@MISX"
    assert ev.side == "BUY"
    assert ev.qty == 1.0
    assert ev.price == 10.0
    assert ev.commission == 0.1