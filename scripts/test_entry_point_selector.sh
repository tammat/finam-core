#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.entry_point_selector import EntryPointSelector

selector = EntryPointSelector(tick_size=0.01, stop_atr_mult=1.5, take_atr_mult=2.0)

intent = {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1}
st = {"last": 80.0, "atr": 0.5}

out = selector.enrich_intent(intent, st)

assert out["entry_type"] == "LIMIT", out
assert out["price"] == 80.01, out
assert out["entry_price"] == 80.01, out
assert out["stop_loss"] == 79.26, out
assert out["take_profit"] == 81.01, out

intent2 = {"symbol": "BRM6@RTSX", "side": "SELL", "qty": 1}
out2 = selector.enrich_intent(intent2, st)

assert out2["price"] == 79.99, out2
assert out2["stop_loss"] == 80.74, out2
assert out2["take_profit"] == 78.99, out2

print("ENTRY_POINT_SELECTOR_OK")
PY
