#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=paper

# run 3 seconds then kill; we only check that it starts and doesn't crash on import
python -m scripts.run_market_pipeline >/tmp/paper_pipeline.log 2>&1 &
pid=$!
sleep 3
kill $pid || true
sleep 0.2

grep -q "Starting PAPER market pipeline" /tmp/paper_pipeline.log
echo "OK: paper pipeline started"
