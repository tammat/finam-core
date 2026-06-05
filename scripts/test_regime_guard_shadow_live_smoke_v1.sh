#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

echo "=== REGIME GUARD SHADOW LIVE SMOKE V1 ==="

python3 -m py_compile \
  src/finam_core/governance/regime_guard_shadow_accumulator.py \
  src/finam_core/governance/regime_guard_advisory_service.py \
  src/finam_core/pipelines/paper_pipeline.py

echo "PRE_RESTART_ROWS"
psql "$DATABASE_URL" -c "
select
  count(*) as rows_before
from research_regime_guard_shadow
where source='regime_guard_shadow_accumulation_v1'
  and created_at >= now() - interval '30 minutes';
"

echo "RESTART_PIPELINE"
sudo systemctl restart finam-paper-pipeline.service

echo "WAIT_FOR_PIPELINE"
sleep 20

echo "JOURNAL_CHECK"
journalctl -u finam-paper-pipeline.service --since "2 minutes ago" --no-pager | \
grep -E "PIPE_REGIME_GUARD_ADVISORY|PIPE_REGIME_GUARD_SHADOW_ACCUMULATION_OK|PIPE_REGIME_GUARD_SHADOW_ACCUMULATION_FAILED|PIPE_REGIME_GUARD_ADVISORY_FAILED|Traceback|ERROR" | \
tail -120 || true

echo "POST_RESTART_ROWS"
psql "$DATABASE_URL" -c "
select
  count(*) as rows_after,
  sum(case when would_block then 1 else 0 end) as would_block,
  sum(case when actual_block then 1 else 0 end) as actual_block
from research_regime_guard_shadow
where source='regime_guard_shadow_accumulation_v1'
  and created_at >= now() - interval '30 minutes';
"

echo "RECENT_ROWS"
psql "$DATABASE_URL" -c "
select
  to_char(created_at at time zone 'Europe/Moscow','DD-MM-YYYY HH24:MI:SS') as created_at_msk,
  symbol,
  strategy,
  regime_key,
  classification,
  would_block,
  actual_block,
  advisory_only,
  reason
from research_regime_guard_shadow
where source='regime_guard_shadow_accumulation_v1'
  and created_at >= now() - interval '30 minutes'
order by created_at desc
limit 20;
"

echo "REGIME_GUARD_SHADOW_LIVE_SMOKE_V1_OK"
