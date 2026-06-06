#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 - <<'PY'
from finam_core.governance.ng_short_block_policy_v1 import NgShortBlockPolicyV1

p = NgShortBlockPolicyV1()

cases = [
    ("NGN6@RTSX", "SELL", 1, 1, True, "CLOSE_LONG"),
    ("NGN6@RTSX", "SELL", 2, 1, True, "REDUCE_LONG"),
    ("NGN6@RTSX", "SELL", 0, 1, False, "OPEN_SHORT"),
    ("NGN6@RTSX", "SELL", -1, 1, False, "ADD_SHORT"),
    ("NGN6@RTSX", "BUY", 0, 1, True, "PASS"),
    ("BRN6@RTSX", "SELL", 0, 1, True, "PASS"),
]

for symbol, side, pos, qty, allowed, action in cases:
    d = p.evaluate(symbol=symbol, side=side, position=pos, quantity=qty)
    print(
        f"NG_SHORT_BLOCK_POLICY_ROW symbol={symbol} side={side} "
        f"pos={pos} qty={qty} allowed={int(d.allowed)} action={d.action} reason={d.reason}"
    )
    assert d.allowed is allowed
    assert d.action == action

print("NG_SHORT_BLOCK_POLICY_V1_OK")
PY
