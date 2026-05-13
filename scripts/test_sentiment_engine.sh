#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python - <<'PY'
from finam_core.ai.sentiment_engine import SentimentEngine, SentimentResult

engine = SentimentEngine()

empty = engine.analyze("")
assert isinstance(empty, SentimentResult)
assert empty.label == "neutral"
assert empty.score == 0.0

print("OK: sentiment_engine import and empty-text test passed")
PY
