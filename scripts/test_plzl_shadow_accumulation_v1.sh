#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_plzl_shadow_accumulation_v1.py
python3 src/scripts/research/build_plzl_shadow_accumulation_v1.py | tee /tmp/plzl_shadow_accumulation_v1.log

grep -q "PLZL SHADOW ACCUMULATION V1" /tmp/plzl_shadow_accumulation_v1.log
grep -q "runtime_allow=0" /tmp/plzl_shadow_accumulation_v1.log
grep -q "execution_enabled=0" /tmp/plzl_shadow_accumulation_v1.log
grep -q "PLZL_SHADOW_ACCUMULATION_V1_OK" /tmp/plzl_shadow_accumulation_v1.log

psql "$DATABASE_URL" -c "\d+ plzl_shadow_accumulation_v1" >/tmp/plzl_shadow_table.txt
grep -q "execution_enabled" /tmp/plzl_shadow_table.txt

echo TEST_PLZL_SHADOW_ACCUMULATION_V1_OK
