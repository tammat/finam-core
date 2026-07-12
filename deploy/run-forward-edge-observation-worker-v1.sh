#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
flock -n /tmp/marketcore-forward-edge-worker-v1.lock \
  env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python src/scripts/run_forward_edge_observation_worker_v1.py
flock -n /tmp/marketcore-forward-edge-relation-router-v1.lock \
  env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python src/scripts/run_forward_edge_relation_router_v1.py
