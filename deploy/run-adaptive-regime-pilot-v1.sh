#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
export PYTHONPATH=/opt/finam-core/src
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL="${DATABASE_URL:-postgresql:///finam_core}"
exec /opt/finam-core/venv/bin/python src/scripts/run_adaptive_regime_pilot_v1.py
