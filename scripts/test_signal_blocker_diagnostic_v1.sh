#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SIGNAL_BLOCKER_DIAGNOSTIC_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'guard_columns=' || string_agg(column_name, ',' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='runtime_guard_pre_signal_block_audit_v1';

SELECT 'recent_guard_blocks=' || count(*)
FROM public.runtime_guard_pre_signal_block_audit_v1
WHERE created_at > now() - interval '2 hours';

SELECT 'block_type=' || block_type || '|count=' || cnt
FROM (
    SELECT block_type, count(*) AS cnt
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
    GROUP BY block_type
) x
ORDER BY cnt DESC, block_type;

SELECT 'reason=' || reason || '|count=' || cnt
FROM (
    SELECT reason, count(*) AS cnt
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
    GROUP BY reason
) x
ORDER BY cnt DESC, reason;

SELECT 'symbol=' || symbol || '|count=' || cnt
FROM (
    SELECT symbol, count(*) AS cnt
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
    GROUP BY symbol
) x
ORDER BY cnt DESC, symbol;

SELECT 'execution_intents_2h=' || count(*)
FROM public.execution_intents
WHERE created_at > now() - interval '2 hours';

SELECT 'orders_2h=' || count(*)
FROM public.orders
WHERE created_ts > now() - interval '2 hours';

SELECT 'fills_2h=' || count(*)
FROM public.fills
WHERE ts > now() - interval '2 hours';

SELECT 'VERDICT=SIGNAL_BLOCKER_DIAGNOSTIC_V1_READY';
SQL

echo "TEST_SIGNAL_BLOCKER_DIAGNOSTIC_V1_OK"
