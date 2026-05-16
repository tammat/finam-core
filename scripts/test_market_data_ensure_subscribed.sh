#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/adapters/grpc/market_data.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/adapters/grpc/market_data.py").read_text(encoding="utf-8")

checks = [
    "def ensure_subscribed(self, symbols: List[str])",
    "self._symbols: list[str] = []",
    "self._active_call.cancel()",
    "active_symbols",
    "SubscribeQuoteRequest(symbols=active_symbols)",
    "MarketData resubscribe requested",
]

for c in checks:
    assert c in text, c

print("OK: MarketData ensure_subscribed supports live resubscribe")
PY
