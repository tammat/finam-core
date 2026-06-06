#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/research/open_short_policy_v1.py \
  src/finam_core/signals/intent_semantics_v2.py \
  src/scripts/analytics/build_br_open_short_policy_research_v1.py

python3 - <<'PY'
from finam_core.research.open_short_policy_v1 import OpenShortPolicyV1

p = OpenShortPolicyV1(mode="shadow")

d1 = p.evaluate(symbol="BRN6@RTSX", strategy="BR_CONSERVATIVE_BREAKOUT", action="OPEN_SHORT")
assert d1.allowed is True
assert d1.reason == "br_open_short_research_allowed"

d2 = p.evaluate(symbol="NGN6@RTSX", strategy="NG_CONSERVATIVE_BREAKOUT_M1", action="OPEN_SHORT")
assert d2.allowed is False
assert d2.reason == "open_short_not_enabled_for_root"

d3 = p.evaluate(symbol="BRN6@RTSX", strategy="BR_CONSERVATIVE_BREAKOUT", action="REDUCE_LONG")
assert d3.allowed is True
assert d3.reason == "not_open_short"

print("OPEN_SHORT_POLICY_UNIT_OK")
PY

python3 src/scripts/analytics/build_br_open_short_policy_research_v1.py | \
  tee /tmp/br_open_short_policy_research_v1.log

grep -q "BR OPEN SHORT POLICY RESEARCH V1" /tmp/br_open_short_policy_research_v1.log
grep -q "OBSERVED_ACTIONS" /tmp/br_open_short_policy_research_v1.log
grep -q "POLICY_DECISIONS_ON_OBSERVED_FLOW" /tmp/br_open_short_policy_research_v1.log
grep -q "OBSERVED_OPEN_SHORT_CANDIDATES" /tmp/br_open_short_policy_research_v1.log
grep -Eq "VERDICT=NO_HISTORICAL_OPEN_SHORT_CANDIDATES_IN_TRADES|VERDICT=OPEN_SHORT_POLICY_CANDIDATES_FOUND" \
  /tmp/br_open_short_policy_research_v1.log

echo BR_OPEN_SHORT_POLICY_RESEARCH_V1_OK
