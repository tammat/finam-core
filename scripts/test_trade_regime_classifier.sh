#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/trade_regime_classifier.py

python - <<'PY'
from datetime import datetime, UTC
from finam_core.analytics.trade_regime_classifier import classify_trade_regime

r = classify_trade_regime(datetime(2026, 5, 11, 9, 30, tzinfo=UTC))

assert r.hour == 9
assert r.market_session == "morning"

print("TRADE_REGIME_CLASSIFIER_OK")
PY
