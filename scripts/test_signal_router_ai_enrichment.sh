#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src
export ENABLE_AI_SENTIMENT_FEATURES=1

python -m py_compile \
  src/finam_core/ai/sentiment_signal_enricher.py \
  src/finam_core/signals/signal_router.py

python - <<'PY'
from finam_core.signals.signal_router import SignalRouter

router = SignalRouter()

routed = router.route({
    "symbol": "SBER@MISX",
    "side": "BUY",
    "qty": 1,
    "price": 300,
    "confidence": 1.0,
    "reason": "ai_enrichment_test",
    "features": {
        "atr": 3.0
    }
})

assert routed.intent is not None
features = routed.intent.features

assert "ai_sentiment_label" in features
assert "ai_sentiment_score" in features
assert "ai_sentiment_source" in features

print("OK: SignalRouter adds AI sentiment features")
print(features)
PY
