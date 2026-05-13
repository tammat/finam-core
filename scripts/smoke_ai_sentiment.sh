#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate
export PYTHONPATH=src

python - <<'PY'
from finam_core.ai.sentiment_engine import SentimentEngine

texts = [
    "Акции Сбера растут на сильной отчетности и улучшении прогноза прибыли.",
    "Цены на нефть падают из-за опасений снижения спроса.",
    "Компания опубликовала нейтральные операционные результаты."
]

engine = SentimentEngine()

for text in texts:
    result = engine.analyze(text)
    print("TEXT:", text)
    print("LABEL:", result.label)
    print("SCORE:", result.score)
    print("RAW:", result.raw)
    print("-" * 80)
PY
