#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD METRICS SUMMARY V1 ==="

python3 -m py_compile src/scripts/research/add_operational_dashboard_metrics_summary_v1.py

python3 src/scripts/research/add_operational_dashboard_metrics_summary_v1.py \
  | tee /tmp/operational_dashboard_metrics_summary_v1.log

grep -q "OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1_OK" /tmp/operational_dashboard_metrics_summary_v1.log
grep -q "runtime_allow=0" /tmp/operational_dashboard_metrics_summary_v1.log
grep -q "execution_enabled=0" /tmp/operational_dashboard_metrics_summary_v1.log

grep -q "operational-metrics-summary-v1" src/ui/templates/v3_dashboard.html
grep -q "Текущих paper-позиций" src/ui/templates/v3_dashboard.html
grep -q "Clean V3 flat" src/ui/templates/v3_dashboard.html
grep -q "В карантине" src/ui/templates/v3_dashboard.html
grep -q "Текущий net qty" src/ui/templates/v3_dashboard.html

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

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
    operational_positions_v1=[
        {
            "symbol": "BRN6@RTSX",
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "timeframe": "M5",
            "net_qty": 5,
            "full_chains": 102,
            "pnl": -124.211906,
            "operational_status": "OPEN_PAPER_LONG_TAIL",
        },
        {
            "symbol": "NGQ6@RTSX",
            "strategy": "NG_CONSERVATIVE_BREAKOUT_M1",
            "timeframe": "M1",
            "net_qty": 0,
            "full_chains": 11,
            "pnl": -0.045360,
            "operational_status": "CLEAN_V3_FLAT",
        },
        {
            "symbol": "USDRUBF@RTSX",
            "strategy": "USD_INTRADAY_REGIME",
            "timeframe": "M5",
            "net_qty": 3,
            "full_chains": 7,
            "pnl": -0.508082,
            "operational_status": "QUARANTINE_CONTAMINATED_TAIL",
        },
        {
            "symbol": "BRM6@RTSX",
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "timeframe": "M5",
            "net_qty": 20,
            "full_chains": 16,
            "pnl": -8.427906,
            "operational_status": "EXCLUDE_HISTORICAL_TAIL",
        },
    ],
)

assert "operational-metrics-summary-v1" in html
assert "Текущих paper-позиций" in html
assert "Текущий net qty" in html
assert "Карантин" in html

print("JINJA_RENDER_OK", len(html))
PY

echo
echo "=== SERVICE RESTART ==="
sudo systemctl restart finam-core-ui-readonly.service

echo
echo "=== WAIT FOR 8088 ==="
ready=0
for i in $(seq 1 20); do
  if curl -fss http://127.0.0.1:8088/ >/tmp/operational_dashboard_metrics_summary_root_v1.html; then
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

grep -q "Текущих paper-позиций" /tmp/operational_dashboard_metrics_summary_root_v1.html
grep -q "Текущий net qty" /tmp/operational_dashboard_metrics_summary_root_v1.html

curl -fss http://127.0.0.1:8088/v3 \
  | tee /tmp/operational_dashboard_metrics_summary_v3_v1.html \
  | grep -q "Clean V3 flat"

echo TEST_OPERATIONAL_DASHBOARD_METRICS_SUMMARY_V1_OK
