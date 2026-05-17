#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_runtime_universe_rotation_log.sql >/dev/null

python -m py_compile src/finam_core/runtime/runtime_universe_rotation_logger.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/runtime/runtime_universe_rotation_logger.py").read_text(encoding="utf-8")

checks = [
    "RuntimeUniverseRotationLogger",
    "log_rotation",
    "runtime_universe_rotation_log",
    "freshness_adjusted_score",
    "previous_status",
    "new_status",
    "json.dumps",
]

for c in checks:
    assert c in text, c

print("OK: RuntimeUniverseRotationLogger static check")
PY

python - <<'PY'
from finam_core.runtime.runtime_universe_rotation_logger import RuntimeUniverseRotationLogger
from finam_core.storage.postgres_logger import PostgresLogger

logger = RuntimeUniverseRotationLogger(PostgresLogger())

logger.log_rotation(
    symbol="TEST@MOEX",
    action="ADD",
    previous_status=None,
    new_status="ACTIVE",
    strategy="TEST_STRATEGY",
    regime="test_regime",
    score=0.9,
    freshness_adjusted_score=0.85,
    reason="test_rotation_logger",
    raw_json={"test": True},
)

print("OK: rotation log inserted")
PY

psql "$DATABASE_URL" -P pager=off -c "
select symbol, action, new_status, reason
from runtime_universe_rotation_log
where symbol = 'TEST@MOEX'
order by created_at desc
limit 1;
"

echo "OK: RuntimeUniverseRotationLogger"
