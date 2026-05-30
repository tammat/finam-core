#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_FINAM_OPS_SH_START"

test -x scripts/ops/finam_ops.sh

bash -n scripts/ops/finam_ops.sh

./scripts/ops/finam_ops.sh help | grep -q "Finam_Core ops commands"
./scripts/ops/finam_ops.sh env >/tmp/finam_ops_env.out || true

echo "TEST_FINAM_OPS_SH_OK"
