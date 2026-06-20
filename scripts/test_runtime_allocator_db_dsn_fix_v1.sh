#!/usr/bin/env bash
set -euo pipefail

echo "=== RUNTIME_ALLOCATOR_DB_DSN_FIX_V1 ==="

python3 -m py_compile src/scripts/run_runtime_universe_allocator.py

sudo -u finam bash -lc '
cd /opt/finam-core || exit 1
source /opt/finam-core/.env
export PYTHONPATH=/opt/finam-core/src
export RUNTIME_ACTIVE_UNIVERSE_LIMIT=8
export RUNTIME_MAX_SYMBOLS=8
/opt/finam-core/venv/bin/python src/scripts/run_runtime_universe_allocator.py
'

psql "$DATABASE_URL" -c "
select symbol, strategy, priority, score, is_enabled
from runtime_active_universe
where symbol like '%@MISX'
order by priority desc;
"

echo "VERDICT=RUNTIME_ALLOCATOR_DB_DSN_FIX_OK"
echo "TEST_RUNTIME_ALLOCATOR_DB_DSN_FIX_V1_OK"
