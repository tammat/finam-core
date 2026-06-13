#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

bash -n scripts/report_br_ng_history.sh

./scripts/report_br_ng_history.sh | tee /tmp/report_br_ng_history.log

grep -q "trades" /tmp/report_br_ng_history.log
grep -q "net_pnl" /tmp/report_br_ng_history.log
grep -q "expectancy" /tmp/report_br_ng_history.log

echo "TEST_REPORT_BR_NG_HISTORY_OK"
