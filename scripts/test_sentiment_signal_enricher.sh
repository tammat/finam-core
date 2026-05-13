#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python -m py_compile src/finam_core/ai/sentiment_signal_enricher.py

python - <<'PY'
from finam_core.ai.sentiment_signal_enricher import SentimentSignalEnricher


class FakeProvider:
    def latest_features_dict(self, symbol):
        return {
            "ai_sentiment_label": "positive",
            "ai_sentiment_score": 0.81,
            "ai_sentiment_source": "unit_test",
            "ai_sentiment_symbol": symbol,
        }


enricher = SentimentSignalEnricher(provider=FakeProvider())
features = enricher.enrich(
    symbol="SBER@MISX",
    features={"base_feature": 123},
)

assert features["base_feature"] == 123
assert features["ai_sentiment_label"] == "positive"
assert features["ai_sentiment_score"] == 0.81
assert features["ai_sentiment_symbol"] == "SBER@MISX"

print("OK: sentiment signal enricher works")
PY
