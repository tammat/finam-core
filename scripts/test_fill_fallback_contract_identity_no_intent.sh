#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert 'fill_symbol = str(getattr(fill, "symbol", None) or payload.get("symbol") or "")' in text
assert 'ContractIdentityResolver.resolve(fill_symbol)' in text
assert 'intent.get("symbol")' not in text[text.find("последний защитный слой metadata"):text.find("persist_result = service.persist_fill")]

print("OK: fallback contract identity enrichment does not depend on intent")
PY
