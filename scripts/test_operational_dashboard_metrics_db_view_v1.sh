#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD METRICS DB VIEW V1 ==="

python3 -m py_compile src/scripts/research/build_clean_operational_position_metrics_view_v1.py
python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

python3 src/scripts/research/build_clean_operational_position_metrics_view_v1.py \
  | tee /tmp/clean_operational_position_metrics_view_v1.log

grep -q "CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_V1_OK" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "VERDICT=CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_READY" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "current_position_count=1" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "clean_flat_count=" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "clean_open_review_count=" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "quarantine_count=1" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "excluded_count=1" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "runtime_allow=0" /tmp/clean_operational_position_metrics_view_v1.log
grep -q "execution_enabled=0" /tmp/clean_operational_position_metrics_view_v1.log

grep -q "OPERATIONAL_DASHBOARD_METRICS_DB_VIEW_V1" src/ui/readonly_runtime_dashboard_v1.py
grep -q "OPERATIONAL_DASHBOARD_METRICS_DB_VIEW_V1" src/ui/templates/v3_dashboard.html
grep -q "operational_metrics_v1" src/ui/templates/v3_dashboard.html

echo
echo "=== SQL METRICS VIEW CHECK ==="
psql "$DATABASE_URL" -c "
select *
from clean_operational_position_metrics_v1;
"

echo
echo "=== JINJA SMOKE TEST ==="
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

template_dir = Path("src/ui/templates")
env = Environment(loader=FileSystemLoader(str(template_dir)))
tpl = env.get_template("v3_dashboard.html")

html = tpl.render(
    request=None,
    data={
        "title": "TEST",
        "mode": "TEST",
        "runtime": "Закрыт",
        "execution": "Закрыто",
        "summary": {
            "strategies": 0,
            "clean_trades": 0,
            "v3_full_chains": 0,
            "v3_pnl": 0,
        },
        "accumulation": [],
        "statistics": [],
        "daily": [],
        "checkpoints": [],
    },
    active="v3",
    operational_positions_error_v1=None,
    operational_metrics_error_v1=None,
    operational_metrics_v1={
        "current_position_count": 1,
        "clean_flat_count": 6,
        "quarantine_count": 1,
        "excluded_count": 1,
        "current_net_qty_sum": 5,
    },
    operational_positions_v1=[
        {
            "symbol": "BRN6@RTSX",
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "timeframe": "M5",
            "net_qty": 5,
            "full_chains": 102,
            "pnl": -124.211906,
            "operational_status": "OPEN_PAPER_LONG_TAIL",
        }
    ],
)

assert "Текущих paper-позиций" in html
assert "Текущий net qty" in html
assert "operational-metrics-summary-v1" in html

print("JINJA_RENDER_OK", len(html))
PY

echo
echo "=== SERVICE RESTART ==="
sudo systemctl restart finam-core-ui-readonly.service

echo
echo "=== WAIT FOR 8088 ==="
ready=0
for i in $(seq 1 20); do
  if curl -fss http://127.0.0.1:8088/ >/tmp/operational_dashboard_metrics_db_view_root_v1.html; then
    ready=1
    echo "8088_READY attempt=${i}"
    break
  fi
  sleep 1
done

if [ "${ready}" != "1" ]; then
  echo "FAIL: 8088 did not become ready after restart"
  exit 1
fi

grep -q "Текущих paper-позиций" /tmp/operational_dashboard_metrics_db_view_root_v1.html
grep -q "Текущий net qty" /tmp/operational_dashboard_metrics_db_view_root_v1.html

curl -fss http://127.0.0.1:8088/v3 \
  | tee /tmp/operational_dashboard_metrics_db_view_v3_v1.html \
  | grep -q "Clean V3 flat"

echo TEST_OPERATIONAL_DASHBOARD_METRICS_DB_VIEW_V1_OK
