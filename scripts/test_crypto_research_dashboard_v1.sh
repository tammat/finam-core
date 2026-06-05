#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/observability/build_crypto_research_dashboard_v1.py

python3 src/scripts/observability/build_crypto_research_dashboard_v1.py | \
  tee /tmp/crypto_research_dashboard_v1.log

grep -q "CRYPTO RESEARCH DASHBOARD V1" /tmp/crypto_research_dashboard_v1.log
grep -q "mode=research_only" /tmp/crypto_research_dashboard_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_CRYPTO_RESEARCH_DATA" /tmp/crypto_research_dashboard_v1.log

echo CRYPTO_RESEARCH_DASHBOARD_V1_OK
