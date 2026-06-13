#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

python3 src/scripts/analytics/build_ng_unvalidated_profile_regime_decomposition_v1.py

echo "TEST_NG_UNVALIDATED_PROFILE_REGIME_DECOMPOSITION_V1_OK"
