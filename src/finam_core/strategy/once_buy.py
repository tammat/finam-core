# src/finam_core/strategy/once_buy.py
# Русский коммент: простая стратегия — один BUY по первому валидному тика.

from __future__ import annotations

import logging

LOG = logging.getLogger(__name__)


class OnceBuyStrategy:
    """Emit a single BUY intent on first valid quote."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.sent = False

    def on_quote(self, state: dict):
        sym = state.get("symbol")
        last = state.get("last")

        if not self.sent:
            LOG.debug("STRATEGY waiting first quote: %s last=%s", sym, last)

        if self.sent or sym != self.symbol or last is None:
            return None

        self.sent = True
        LOG.info("STRATEGY EMIT INTENT")
        return {"symbol": sym, "side": "BUY", "qty": 1.0}
