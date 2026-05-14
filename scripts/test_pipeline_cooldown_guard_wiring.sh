#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/cooldown_guard.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "CooldownGuard" src/finam_core/pipelines/paper_pipeline.py
grep -q "calculate_dynamic_cooldown" src/finam_core/pipelines/paper_pipeline.py
grep -q "check_elapsed" src/finam_core/pipelines/paper_pipeline.py

echo "OK: pipeline cooldown guard wiring"
