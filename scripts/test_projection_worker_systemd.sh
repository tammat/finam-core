#!/usr/bin/env bash
set -euo pipefail

test -f systemd/finam-projection-worker.service
grep -q "Finam Core Projection Worker" systemd/finam-projection-worker.service
grep -q "WorkingDirectory=/opt/finam-core" systemd/finam-projection-worker.service
grep -q "python -m finam_core.projections.projection_worker" systemd/finam-projection-worker.service
grep -q "Restart=always" systemd/finam-projection-worker.service
grep -q "def main()" src/finam_core/projections/projection_worker.py

echo "PROJECTION_WORKER_SYSTEMD_OK"
