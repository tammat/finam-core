#!/bin/bash
set -euo pipefail

cd /opt/finam-core
exec 9>/tmp/marketcore-forward-edge-regime-refresh-v1.lock
flock -n 9 || exit 0

export DATABASE_URL="${DATABASE_URL:-postgresql:///finam_core}"
export PYTHONPATH=/opt/finam-core/src
export PYTHONDONTWRITEBYTECODE=1

.venv/bin/python src/scripts/build_historical_regime_snapshots_v2.py --symbols IMOEX,IMOEX2 --timeframe M5
.venv/bin/python src/scripts/backfill_forward_edge_context_v1.py
.venv/bin/python src/scripts/build_forward_edge_regime_attribution_v1.py
