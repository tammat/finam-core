#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.portfolio.position_intent import PositionIntentClassifier

c = PositionIntentClassifier()

br = c.classify("BRM6@RTSX")
assert br.horizon == "intraday", br
assert br.allow_intraday_exit is True, br
assert br.allow_trailing is True, br

plzl = c.classify("PLZL@MISX")
assert plzl.horizon == "swing", plzl
assert plzl.allow_intraday_exit is False, plzl
assert plzl.allow_trailing is True, plzl

eutr = c.classify("EUTR@MISX")
assert eutr.horizon == "long_term", eutr
assert eutr.allow_intraday_exit is False, eutr
assert eutr.allow_trailing is False, eutr
assert eutr.allow_new_buy is False, eutr

unknown = c.classify("UNKNOWN@MISX")
assert unknown.horizon == "swing", unknown

print("POSITION_INTENT_OK")
PY
