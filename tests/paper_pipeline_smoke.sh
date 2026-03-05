#!/usr/bin/env bash
set -euo pipefail
export RUN_SECS=5
export PYTHONPATH=src
export EXECUTION_MODE=paper

python -m scripts.run_market_pipeline >/tmp/paper_pipeline.log 2>&1 &
pid=$!

sleep 3

# процесс мог уже завершиться — это ок для smoke; не валим тест на kill
kill "$pid" 2>/dev/null || true
sleep 0.2

echo "---- LOG TAIL ----"
tail -n 60 /tmp/paper_pipeline.log || true
echo "------------------"

# MUST start marker
grep -q "Starting PAPER market pipeline" /tmp/paper_pipeline.log

# MUST NOT have obvious crashes
if grep -Eqi "Traceback|ImportError|ModuleNotFoundError" /tmp/paper_pipeline.log; then
  echo "FAIL: crash detected in log"
  exit 1
fi

echo "OK: paper pipeline smoke"