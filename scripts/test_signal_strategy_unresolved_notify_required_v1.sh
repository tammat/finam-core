#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL STRATEGY UNRESOLVED NOTIFY REQUIRED V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/finam_core/strategy/signal_strategy_attribution_gate_v1.py \
  src/finam_core/strategy/signal_strategy_discovery_repository_v1.py \
  src/scripts/research/test_signal_strategy_unresolved_notify_required_v1.py

PYTHONPATH=src python3 src/scripts/research/test_signal_strategy_unresolved_notify_required_v1.py \
  | tee /tmp/signal_strategy_unresolved_notify_required_v1.log

grep -q "SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED_V1_OK" /tmp/signal_strategy_unresolved_notify_required_v1.log
grep -q "SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED" /tmp/signal_strategy_unresolved_notify_required_v1.log
grep -q "ATTRIBUTION_DECISION allowed=0" /tmp/signal_strategy_unresolved_notify_required_v1.log
grep -q "discovery_required=1" /tmp/signal_strategy_unresolved_notify_required_v1.log
grep -q "discovery_event_id=" /tmp/signal_strategy_unresolved_notify_required_v1.log

sudo -u postgres psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
\pset pager off

select
    'DISCOVERY_EVENT_TABLE_OK' as check_name,
    count(*) as total_events,
    count(*) filter (where status = 'NEW') as new_events
from signal_strategy_discovery_events;

select
    id,
    symbol,
    reason,
    source,
    status,
    proposed_strategy,
    proposed_timeframe,
    proposed_continuous_symbol,
    created_at
from signal_strategy_discovery_events
order by id desc
limit 5;
SQL


sudo -u postgres psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL' | tee /tmp/signal_strategy_unresolved_unknown_status_v1.log
\pset pager off

select
    'UNKNOWN_TEST_EVENTS_STATUS' as check_name,
    count(*) filter (where status = 'NEW') as new_unknown_events,
    count(*) filter (where status = 'TEST_CLOSED') as test_closed_unknown_events
from signal_strategy_discovery_events
where symbol = 'UNKNOWN@RTSX';
SQL

grep -q "UNKNOWN_TEST_EVENTS_STATUS" /tmp/signal_strategy_unresolved_unknown_status_v1.log
grep -Eq "UNKNOWN_TEST_EVENTS_STATUS[[:space:]]+\|[[:space:]]+0[[:space:]]+\|" /tmp/signal_strategy_unresolved_unknown_status_v1.log

echo UNKNOWN_TEST_EVENTS_NO_NEW_OK

echo TEST_SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED_V1_OK
