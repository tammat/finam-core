#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 - <<'PY'
from finam_core.governance.br_short_shadow_policy_v1 import BrShortShadowPolicyV1

p = BrShortShadowPolicyV1()

d = p.evaluate(symbol="BRN6@RTSX", side="SELL", strategy="BR_CONSERVATIVE_BREAKOUT", current_position=0)
assert d.allowed is True
assert d.shadow_logged is True
assert d.reason == "br_short_shadow_open_short_candidate"

d = p.evaluate(symbol="BRN6@RTSX", side="SELL", strategy="BR_CONSERVATIVE_BREAKOUT", current_position=2)
assert d.allowed is True
assert d.shadow_logged is False
assert d.reason == "br_sell_reduces_existing_long"

d = p.evaluate(symbol="BRN6@RTSX", side="SELL", strategy="BR_CONSERVATIVE_BREAKOUT_M5", current_position=0)
assert d.allowed is False
assert d.shadow_logged is True

d = p.evaluate(symbol="NGN6@RTSX", side="SELL", strategy="NG_CONSERVATIVE_BREAKOUT_M1", current_position=0)
assert d.allowed is True
assert d.shadow_logged is False

print("BR_SHORT_SHADOW_POLICY_V1_OK")
PY
