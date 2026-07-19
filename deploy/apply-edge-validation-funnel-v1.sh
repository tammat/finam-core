#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
until psql -d finam_core -v ON_ERROR_STOP=1 \
    -c "SET lock_timeout='250ms'" \
    -f sql/analytics/123_edge_validation_funnel_v1.sql; do
    sleep 30
done
psql -d finam_core -v ON_ERROR_STOP=1 \
    -f sql/presentation/125_research_validation_funnel_i18n_v1.sql

main_pid="$(systemctl show -p MainPID --value marketcore-ui-shell.service)"
if [[ "$main_pid" =~ ^[1-9][0-9]*$ ]]; then
    kill "$main_pid"
fi
