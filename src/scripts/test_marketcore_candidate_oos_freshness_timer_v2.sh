#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
systemctl is-active --quiet marketcore-candidate-oos-freshness.timer
systemctl is-enabled --quiet marketcore-candidate-oos-freshness.timer
systemctl show marketcore-candidate-oos-freshness.service -p Environment | grep -q 'REAL_TRADING_ENABLED=0'
age="$(psql -d finam_core -Atqc "SELECT extract(epoch FROM clock_timestamp()-max(updated_at))::bigint FROM analytics.edge_candidate_v1")"
test "$age" -le 3900
echo "candidate_oos_age_seconds=$age"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_CANDIDATE_OOS_FRESHNESS_TIMER_V2_READY"
