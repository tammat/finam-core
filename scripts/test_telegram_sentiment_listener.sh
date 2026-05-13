#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python -m py_compile src/finam_core/ai/telegram_sentiment_listener.py

python - <<'PY'
from finam_core.ai.telegram_sentiment_listener import TelegramSentimentListener, TelegramSentimentEvent


class FakeEngine:
    def analyze(self, text):
        class Result:
            label = "positive"
            score = 0.77
            raw = {"label": "positive", "score": 0.77}
        return Result()


listener = TelegramSentimentListener(engine=FakeEngine())
event = listener.analyze_message(
    text="Тестовая позитивная новость",
    source="unit_test",
)

assert isinstance(event, TelegramSentimentEvent)
assert event.source == "unit_test"
assert event.label == "positive"
assert event.score == 0.77
assert "Тестовая" in event.text

print("OK: telegram_sentiment_listener safe test passed")
PY

if grep -R "place_order\|PlaceOrder\|finam_client\|TradeAPI\|OrdersService\|place_limit_order\|place_market_order" -n src/finam_core/ai/telegram_sentiment_listener.py; then
  echo "ERROR: unsafe trading-related reference found"
  exit 1
fi

echo "OK: no trading API references found"
