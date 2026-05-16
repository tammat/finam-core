#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

marker = "последний защитный слой metadata"
start = text.find(marker)
assert start != -1, "fallback metadata marker not found"

end = text.find("persist_result = service.persist_fill", start)
assert end != -1, "persist_fill call after fallback metadata not found"

fallback_block = text[start:end]

assert 'payload.setdefault("strategy", payload.get("strategy") or self._strategy_name_for_symbol(fill_symbol))' in fallback_block
assert 'payload.setdefault("source", payload.get("source") or "paper_fill_fallback")' in fallback_block
assert 'payload.setdefault("confidence", payload.get("confidence") or 1.0)' in fallback_block
assert 'payload.setdefault("attribution_version", "strategy_attribution_v1")' in fallback_block

assert 'intent.get("strategy") or (intent.get("features") or {}).get("strategy")' not in fallback_block

print("OK: fallback metadata in _on_fill does not require intent scope")
PY
