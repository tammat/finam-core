#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "REGIME_ENGINE_LOG_EVERY_SEC" src/finam_core/regime/regime_engine.py
grep -q "_last_regime_engine_log_ts" src/finam_core/regime/regime_engine.py
grep -q "_last_regime_engine_log_key" src/finam_core/regime/regime_engine.py
grep -q "log_key != self._last_regime_engine_log_key" src/finam_core/regime/regime_engine.py

python -m py_compile src/finam_core/regime/regime_engine.py

echo "REGIME_ENGINE_LOG_RATE_LIMIT_TEST_OK"
