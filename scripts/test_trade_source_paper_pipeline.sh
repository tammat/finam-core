#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "trade_source" src/scripts/replay_br_pipeline.py
grep -q '"paper"' src/scripts/replay_br_pipeline.py
grep -q "trade_source" src/finam_core/storage/postgres.py
grep -q '"paper"' src/finam_core/storage/postgres.py
grep -q "trade_source" src/storage/postgres.py
grep -q '"paper"' src/storage/postgres.py

! grep -R "INSERT INTO trades .*raw_json" src --exclude-dir="__pycache__" >/dev/null
! grep -R "INSERT INTO trades .*quantity, price, ts" src --exclude-dir="__pycache__" >/dev/null
! grep -R "ON CONFLICT (trade_id)" src --exclude-dir="__pycache__" >/dev/null

python -m py_compile src/scripts/replay_br_pipeline.py
python -m py_compile src/finam_core/storage/postgres.py
python -m py_compile src/storage/postgres.py

echo "TRADE_SOURCE_PAPER_PIPELINE_TEST_OK"
