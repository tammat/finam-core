#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

echo "=== TEST_PROJECT_MASTER_CONTEXT_V1 ==="

python3 -m py_compile core/project_state.py
python3 core/project_state.py

grep -Fq "RESEARCH / SHADOW / REAL EXECUTION DISABLED" PROJECT_STATE.md
grep -Fq "PROJECT_STATE_FACTUAL_RECONCILIATION_V1" PROJECT_STATE.md
grep -Fq "SQLite запрещен" PROJECT_STATE.md
grep -Fq "AI-слой не имеет права отправлять ордера напрямую" PROJECT_STATE.md

echo "VERDICT=TEST_PROJECT_MASTER_CONTEXT_V1_OK"
