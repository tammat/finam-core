#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/replay_campaign_performance_summary.py
python src/scripts/replay_campaign_performance_summary.py --help >/dev/null

echo "OK: replay_campaign_performance_summary compile"
