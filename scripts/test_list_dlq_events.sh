#!/usr/bin/env bash
set -euo pipefail

test -x scripts/list_dlq_events.sh

grep -q "event_dead_letters" scripts/list_dlq_events.sh
grep -q "DLQ_LIST_OK" scripts/list_dlq_events.sh
grep -q "resolved" scripts/list_dlq_events.sh

echo "DLQ_LIST_SCRIPT_OK"
