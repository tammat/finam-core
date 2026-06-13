#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

python3 src/scripts/analytics/build_ng_signal_quality_decomposition_v1.py

echo "TEST_NG_SIGNAL_QUALITY_DECOMPOSITION_V1_OK"
