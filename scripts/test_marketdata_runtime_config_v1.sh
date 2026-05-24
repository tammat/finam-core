#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/config/runtime_config.py \
  src/finam_core/adapters/grpc/market_data.py \
  src/scripts/run_market_pipeline.py

grep -R -q "RuntimeConfig" \
  src/finam_core/adapters/grpc \
  src/finam_core/infra/finam

grep -R -q 'runtime_config.get_float("MD_RECONNECT_INITIAL_SEC"' src
grep -R -q 'runtime_config.get_float("MD_RECONNECT_MAX_SEC"' src
grep -R -q 'runtime_config.get_float("MD_FIRST_QUOTE_GRACE_SEC"' src
grep -R -q 'runtime_config.get("MD_WATCHDOG_MODE"' src
grep -R -q 'runtime_config.get_bool("MD_DEBUG"' src

if grep -R -q 'os.getenv("MD_RECONNECT_INITIAL_SEC"' src/finam_core; then
    echo "DIRECT_MD_RECONNECT_INITIAL_SEC_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -R -q 'os.getenv("MD_RECONNECT_MAX_SEC"' src/finam_core; then
    echo "DIRECT_MD_RECONNECT_MAX_SEC_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -R -q 'os.getenv("MD_FIRST_QUOTE_GRACE_SEC"' src/finam_core; then
    echo "DIRECT_MD_FIRST_QUOTE_GRACE_SEC_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -R -q 'os.getenv("MD_WATCHDOG_MODE"' src/finam_core; then
    echo "DIRECT_MD_WATCHDOG_MODE_GETENV_STILL_PRESENT"
    exit 1
fi

if grep -R -q 'os.getenv("MD_DEBUG"' src/finam_core; then
    echo "DIRECT_MD_DEBUG_GETENV_STILL_PRESENT"
    exit 1
fi

echo "MARKETDATA_RUNTIME_CONFIG_V1_OK"
