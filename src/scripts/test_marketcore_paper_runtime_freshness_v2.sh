#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

systemctl is-active --quiet marketcore-paper-runtime-freshness.timer
systemctl is-active --quiet marketcore-runtime-observation-freshness.timer

paper_age="$(psql -d finam_core -Atqc "SELECT extract(epoch FROM clock_timestamp()-refreshed_at)::bigint FROM marketcore_ui.paper_runtime_summary_v1 WHERE id=1")"
runtime_age="$(psql -d finam_core -Atqc "SELECT extract(epoch FROM clock_timestamp()-max(observed_at))::bigint FROM public.runtime_observations")"
test "$paper_age" -le 360
test "$runtime_age" -le 120

systemctl show marketcore-paper-runtime-freshness.service -p Environment | grep -q 'REAL_TRADING_ENABLED=0'
systemctl show marketcore-runtime-observation-freshness.service -p Environment | grep -q 'REAL_TRADING_ENABLED=0'

echo "paper_source_age_seconds=$paper_age"
echo "runtime_source_age_seconds=$runtime_age"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "VERDICT=MARKETCORE_STAGE7_PAPER_RUNTIME_FRESHNESS_V2_READY"
