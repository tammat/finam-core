#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NGQ6 RUNTIME UNIVERSE SEED V1 ==="
echo "mode=manual_seed"
echo "runtime_allow=0"
echo "execution_enabled=0"

psql "$DATABASE_URL" -c "
insert into runtime_active_universe (
    symbol,
    strategy,
    timeframe,
    regime,
    score,
    priority,
    is_enabled,
    allocated_at,
    last_seen_at,
    source,
    raw_json,
    updated_at
)
values (
    'NGQ6@RTSX',
    'NG_CONSERVATIVE_BREAKOUT_M1',
    'M1',
    '',
    0,
    90,
    true,
    now(),
    now(),
    'manual_forward_accumulation_seed',
    jsonb_build_object(
        'reason', 'ngq6_forward_accumulation',
        'runtime_allow', false,
        'execution_enabled', false
    ),
    now()
)
on conflict (symbol, strategy, timeframe)
do update set
    is_enabled=true,
    priority=90,
    last_seen_at=now(),
    source='manual_forward_accumulation_seed',
    raw_json=jsonb_build_object(
        'reason', 'ngq6_forward_accumulation',
        'runtime_allow', false,
        'execution_enabled', false
    ),
    updated_at=now(),
    disabled_at=null,
    disable_reason=null;
"

rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from runtime_active_universe
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and is_enabled=true
  and runtime_allowed is not true
  and execution_enabled is not true;
" 2>/dev/null || psql "$DATABASE_URL" -At -c "
select count(*)
from runtime_active_universe
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and is_enabled=true;
")

echo "ngq6_runtime_universe_rows=${rows}"

if [ "${rows}" = "0" ]; then
  echo "FAIL: NGQ6 runtime universe seed not persisted"
  exit 1
fi

psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    priority,
    is_enabled,
    source,
    updated_at
from runtime_active_universe
where symbol='NGQ6@RTSX'
order by strategy,timeframe;
"

echo "NGQ6_RUNTIME_UNIVERSE_SEED_V1_OK"
