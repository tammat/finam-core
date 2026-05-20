#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/client_order_id_factory.py \
  src/scripts/run_real_buy_execution_adapter.py \
  src/scripts/run_real_sell_execution_adapter.py

grep -q "ClientOrderIdFactory" src/scripts/run_real_buy_execution_adapter.py
grep -q "ClientOrderIdFactory" src/scripts/run_real_sell_execution_adapter.py
grep -q "client_order_id" src/scripts/run_real_buy_execution_adapter.py
grep -q "client_order_id" src/scripts/run_real_sell_execution_adapter.py
grep -q "real_buy_market_pre_persist_before_broker_call" src/scripts/run_real_buy_execution_adapter.py
grep -q "real_sell_pre_persist_before_broker_call" src/scripts/run_real_sell_execution_adapter.py

echo "OK: client order id pre persist"
