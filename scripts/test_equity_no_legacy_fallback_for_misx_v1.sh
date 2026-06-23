#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_NO_LEGACY_FALLBACK_FOR_MISX_V1 ==="

python3 -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q "EQUITY_NO_LEGACY_FALLBACK_FOR_MISX_V1" src/finam_core/pipelines/paper_pipeline.py
grep -q 'return "VOLATILITY_BREAKOUT_EQUITY"' src/finam_core/pipelines/paper_pipeline.py

echo "VERDICT=EQUITY_NO_LEGACY_FALLBACK_FOR_MISX_OK"
echo "TEST_EQUITY_NO_LEGACY_FALLBACK_FOR_MISX_V1_OK"
