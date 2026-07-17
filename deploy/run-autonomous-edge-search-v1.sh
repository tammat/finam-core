#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
mkdir -p runtime/logs
exec nice -n 15 ionice -c 2 -n 7 \
  env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  venv/bin/python src/scripts/run_autonomous_edge_search_cycle_v1.py \
  >>runtime/logs/autonomous-edge-search-v1.log 2>&1
