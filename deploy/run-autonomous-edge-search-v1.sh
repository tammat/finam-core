#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
mkdir -p runtime/logs
exec env PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  venv/bin/python src/scripts/run_autonomous_edge_search_cycle_v1.py \
  >>runtime/logs/autonomous-edge-search-v1.log 2>&1
