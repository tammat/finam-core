#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/quote_normalizer.py

python - <<'PY'
from finam_core.pipelines.quote_normalizer import QuoteNormalizer, NormalizedQuote

q = QuoteNormalizer.normalize({
    "symbol": "BRM6@RTSX",
    "price": 105.5,
    "bid": 105.4,
    "ask": 105.6,
    "atr": 0.4,
    "source": "test",
})

assert isinstance(q, NormalizedQuote)
assert q.symbol == "BRM6@RTSX"
assert q.price == 105.5
assert q.bid == 105.4
assert q.ask == 105.6
assert q.atr == 0.4
assert q.source == "test"

q2 = QuoteNormalizer.normalize({
    "symbol": "LKOH@MISX",
    "last_price": "5200.5",
})

assert q2.symbol == "LKOH@MISX"
assert q2.price == 5200.5

print("OK: QuoteNormalizer")
PY
