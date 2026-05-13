#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python -m py_compile \
  src/finam_core/ai/sentiment_event_repository.py \
  src/finam_core/ai/telegram_sentiment_listener.py

python - <<'PY'
from finam_core.ai.telegram_sentiment_listener import TelegramSentimentListener
from finam_core.ai.sentiment_event_repository import SentimentEventRepository


class FakeEngine:
    def analyze(self, text):
        class Result:
            label = "positive"
            score = 0.91
            raw = {
                "label": "positive",
                "score": 0.91,
                "test": True,
            }
        return Result()


repo = SentimentEventRepository()

listener = TelegramSentimentListener(
    engine=FakeEngine(),
    repository=repo,
)

event = listener.analyze_message(
    text="Тестовое AI-событие PostgreSQL",
    source="repository_test",
)

assert event.label == "positive"
assert event.score == 0.91

print("OK: AI sentiment event stored")
PY

sudo -u postgres psql -d finam_core -c "
SELECT
    id,
    ts,
    source,
    label,
    score,
    left(text, 80) AS text
FROM ai_sentiment_events
ORDER BY id DESC
LIMIT 5;
"
