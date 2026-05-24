#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/config/runtime_config.py

python - <<'PY'
import os
from finam_core.config.runtime_config import RuntimeConfig

os.environ["RUNTIME_CONFIG_TEST_KEY"] = "123"
cfg = RuntimeConfig(database_url="")
assert cfg.get("RUNTIME_CONFIG_TEST_KEY") == "123"
assert cfg.get_int("RUNTIME_CONFIG_TEST_KEY") == 123
assert cfg.get_bool("MISSING_BOOL", default=True) is True
assert cfg.get_float("MISSING_FLOAT", default=1.5) == 1.5

print("RUNTIME_CONFIG_V1_UNIT_OK")
PY

grep -q "runtime_config" scripts/migrate_runtime_config_v1.sh
grep -q "class RuntimeConfig" src/finam_core/config/runtime_config.py

echo "RUNTIME_CONFIG_V1_TEST_OK"
