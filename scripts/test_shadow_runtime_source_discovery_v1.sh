#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_SOURCE_DISCOVERY_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/discover_shadow_runtime_sources_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/discover_shadow_runtime_sources_v1.py | tee /tmp/shadow_runtime_sources_v1.txt

grep -q "VERDICT=SHADOW_RUNTIME_SOURCE_DISCOVERY_V1_READY" /tmp/shadow_runtime_sources_v1.txt

echo "VERDICT=TEST_SHADOW_RUNTIME_SOURCE_DISCOVERY_V1_OK"
