#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PAPER_COST_MODEL_V1_1_RAW_JSON_START"

python -m py_compile \
  src/finam_core/execution/paper_cost_model.py \
  src/finam_core/execution/paper_engine.py \
  src/finam_core/storage/postgres_logger.py

grep -q '"commission_rub": normalized_commission' src/finam_core/storage/postgres_logger.py
grep -q '"currency": getattr(fill, "currency", "RUB")' src/finam_core/storage/postgres_logger.py
grep -q '"broker_commission_rub"' src/finam_core/storage/postgres_logger.py
grep -q '"exchange_commission_rub"' src/finam_core/storage/postgres_logger.py
grep -q '"tax_rub"' src/finam_core/storage/postgres_logger.py
grep -q '"net_cost_rub"' src/finam_core/storage/postgres_logger.py

./scripts/test_paper_cost_model_v1_1.sh

echo "TEST_PAPER_COST_MODEL_V1_1_RAW_JSON_OK"
