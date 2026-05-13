#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python -m py_compile \
  src/finam_core/ai/sentiment_feature_provider.py \
  src/finam_core/ai/sentiment_event_repository.py

python - <<'PY'
from datetime import datetime, timezone

from finam_core.ai.sentiment_events import TelegramSentimentEvent
from finam_core.ai.sentiment_event_repository import SentimentEventRepository
from finam_core.ai.sentiment_feature_provider import SentimentFeatureProvider


repo = SentimentEventRepository()

event = TelegramSentimentEvent(
    ts=datetime.now(timezone.utc).isoformat(),
    source="feature_provider_test",
    text="Позитивный тестовый сигнал для SBER",
    label="positive",
    score=0.88,
    raw={"label": "positive", "score": 0.88, "test": True},
)

repo.save(event, symbol="SBER@MISX")

provider = SentimentFeatureProvider(repository=repo)
features = provider.latest_features_dict(symbol="SBER@MISX")

assert features["ai_sentiment_label"] == "positive"
assert abs(features["ai_sentiment_score"] - 0.88) < 0.000001
assert features["ai_sentiment_source"] == "feature_provider_test"
assert features["ai_sentiment_symbol"] == "SBER@MISX"

print("OK: sentiment features loaded from PostgreSQL")
print(features)
PY
