#!/bin/bash
set -euo pipefail

cd /opt/finam-core
exec 9>/tmp/marketcore-session-execution-edge-refresh-v1.lock
flock -n 9 || exit 0

export DATABASE_URL="${DATABASE_URL:-postgresql:///finam_core}"
export PYTHONPATH=/opt/finam-core/src
export PYTHONDONTWRITEBYTECODE=1

.venv/bin/python src/scripts/build_session_execution_edge_v1.py
