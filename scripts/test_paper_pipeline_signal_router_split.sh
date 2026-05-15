#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.signals.signal_router import SignalRouter as SignalIntentRouter" in text
assert "from finam_core.strategy.signal_router import SignalRouteInput, SignalRouter as QuoteSignalRouter" in text
assert "self.signal_router = QuoteSignalRouter(self.quote_signal_processor)" in text
assert "self.signal_intent_router = SignalIntentRouter()" in text
assert "routed = self.signal_intent_router.route(raw_intent)" in text

print("OK: quote-router и intent-router разделены")
PY
