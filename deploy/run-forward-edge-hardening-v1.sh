#!/bin/bash
set -euo pipefail

cd /opt/finam-core
set -a
source .env
set +a

export DATABASE_URL="${DATABASE_URL:-postgresql:///finam_core}"
export PYTHONPATH=/opt/finam-core/src
export PYTHONDONTWRITEBYTECODE=1

.venv/bin/python -m pytest -q \
  tests/test_forward_edge_shadow_trailing_v1.py \
  tests/test_signal_funnel_analytics_v1.py \
  tests/test_forward_edge_regime_attribution_v1.py \
  tests/test_forward_edge_regime_promotion_gate_v1.py \
  tests/test_forward_edge_loss_decomposition_v1.py \
  tests/test_microstructure_health_v1.py \
  tests/test_finam_microstructure_ws_watchdog_v1.py

psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/analytics/047_forward_edge_regime_attribution_v1.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/analytics/048_forward_edge_regime_promotion_gate_v1.sql
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f sql/analytics/049_forward_edge_loss_decomposition_v1.sql

.venv/bin/python src/scripts/project_forward_edge_shadow_trailing_v1.py
.venv/bin/python src/scripts/signal_funnel_analytics_v1.py
.venv/bin/python src/scripts/build_historical_regime_snapshots_v2.py --symbols IMOEX --timeframe M5
.venv/bin/python src/scripts/build_forward_edge_regime_attribution_v1.py
.venv/bin/python src/scripts/build_forward_edge_regime_promotion_gate_v1.py
.venv/bin/python src/scripts/build_forward_edge_loss_decomposition_v1.py
.venv/bin/python src/scripts/build_microstructure_health_v1.py

deploy/install-marketcore-user-health-timer-v1.sh

echo "promotion_allowed=0"
echo "live_allowed=0"
echo "broker_orders=0"
echo "VERDICT=FORWARD_EDGE_HARDENING_V1_DEPLOYED"
