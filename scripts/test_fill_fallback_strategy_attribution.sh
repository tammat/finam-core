#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert 'identity.continuous if identity.is_futures else fill_symbol' in text
assert 'payload.setdefault("confidence", payload.get("confidence") or 1.0)' in text
assert 'payload.setdefault("attribution_version", "strategy_attribution_v1")' in text

print("OK: fallback fill strategy attribution enrichment exists")
PY
