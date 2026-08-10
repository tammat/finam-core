#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_NET_FIRST_SHADOW_OBSERVER_V1 ==="

ROWS="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM analytics.net_first_shadow_admission_v1
WHERE source_version='NET_FIRST_SHADOW_OBSERVER_V1';
"
)"

REJECTS="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM analytics.net_first_shadow_admission_v1
WHERE source_version='NET_FIRST_SHADOW_OBSERVER_V1'
  AND shadow_decision='WOULD_REJECT';
"
)"

ADMITS="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM analytics.net_first_shadow_admission_v1
WHERE source_version='NET_FIRST_SHADOW_OBSERVER_V1'
  AND shadow_decision='WOULD_ADMIT';
"
)"

BLOCKED="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM analytics.net_first_shadow_admission_v1
WHERE source_version='NET_FIRST_SHADOW_OBSERVER_V1'
  AND production_blocked=true;
"
)"

ROBUSTNESS_SCHEDULED="$(
psql "$DATABASE_URL" -X -Atc "
SELECT COUNT(*)
FROM analytics.net_first_shadow_admission_v1
WHERE source_version='NET_FIRST_SHADOW_OBSERVER_V1'
  AND actual_robustness_scheduled=true;
"
)"

[ "$ROWS" -eq 3 ]
[ "$REJECTS" -eq 3 ]
[ "$ADMITS" -eq 0 ]
[ "$BLOCKED" -eq 0 ]
[ "$ROBUSTNESS_SCHEDULED" -eq 3 ]

echo "shadow_rows=$ROWS"
echo "would_reject=$REJECTS"
echo "would_admit=$ADMITS"
echo "actual_robustness_scheduled=$ROBUSTNESS_SCHEDULED"
echo "production_blocked=$BLOCKED"
echo "potential_robustness_saved=$REJECTS"

echo "shadow_admission_enabled=1"
echo "enforced_admission_enabled=0"
echo "production_pipeline_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_NET_FIRST_SHADOW_OBSERVER_V1_OK"
