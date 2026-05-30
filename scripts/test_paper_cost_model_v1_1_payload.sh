#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PAPER_COST_MODEL_V1_1_PAYLOAD_START"

python -m py_compile \
  src/finam_core/storage/postgres_logger.py \
  src/finam_core/execution/paper_cost_model.py \
  src/finam_core/execution/paper_engine.py

grep -q '"commission_rub": normalized_commission' src/finam_core/storage/postgres_logger.py
grep -q '"currency": getattr(fill, "currency", "RUB")' src/finam_core/storage/postgres_logger.py
grep -q '"broker_commission_rub"' src/finam_core/storage/postgres_logger.py
grep -q '"exchange_commission_rub"' src/finam_core/storage/postgres_logger.py
grep -q '"tax_rub"' src/finam_core/storage/postgres_logger.py
grep -q '"net_cost_rub"' src/finam_core/storage/postgres_logger.py

echo "TEST_PAPER_COST_MODEL_V1_1_PAYLOAD_OK"
