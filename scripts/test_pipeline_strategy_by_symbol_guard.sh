#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "self.strategy_by_symbol = getattr(self, \"strategy_by_symbol\", {})" \
  src/finam_core/pipelines/paper_pipeline.py

echo "OK: strategy_by_symbol guard configured"
