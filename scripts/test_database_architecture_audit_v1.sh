#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_database_architecture_audit_v1.py

python3 \
  src/scripts/research/build_database_architecture_audit_v1.py \
  | tee /tmp/database_architecture_audit_v1.log

grep -q "DATABASE ARCHITECTURE AUDIT V1" \
  /tmp/database_architecture_audit_v1.log

grep -q "DB_TABLE_TOTAL" \
  /tmp/database_architecture_audit_v1.log

grep -q "DATABASE_ARCHITECTURE_VERDICT" \
  /tmp/database_architecture_audit_v1.log

grep -q "DATABASE_ARCHITECTURE_AUDIT_V1_OK" \
  /tmp/database_architecture_audit_v1.log

echo TEST_DATABASE_ARCHITECTURE_AUDIT_V1_OK
