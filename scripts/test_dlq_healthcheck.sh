#!/usr/bin/env bash
set -euo pipefail

test -x scripts/check_dlq_health.sh

grep -q "event_dead_letters" scripts/check_dlq_health.sh
grep -q "resolved = false" scripts/check_dlq_health.sh
grep -q "DLQ_HEALTH_OK" scripts/check_dlq_health.sh
grep -q "DLQ_HEALTH_WARNING" scripts/check_dlq_health.sh

echo "DLQ_HEALTHCHECK_SCRIPT_OK"
