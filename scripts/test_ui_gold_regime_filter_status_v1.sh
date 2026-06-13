#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

grep -q "fetch_gold_regime_filter_status_v1" src/ui/readonly_runtime_dashboard_v1.py
grep -q '"/gold-regime-filter"' src/ui/readonly_runtime_dashboard_v1.py
grep -q "Фильтр GOLD" src/ui/templates/base.html
grep -q "GOLD: обязательный regime-фильтр" src/ui/templates/gold_regime_filter.html
grep -q "up_impulse_sell_block" src/ui/templates/gold_regime_filter.html || true

grep -R "@app.post" src/ui && exit 1 || true
grep -R "@app.put" src/ui && exit 1 || true
grep -R "@app.delete" src/ui && exit 1 || true
grep -RniE "INSERT INTO|UPDATE |DELETE FROM|TRUNCATE |ALTER TABLE|DROP TABLE" src/ui && exit 1 || true

sudo systemctl restart finam-core-ui-readonly.service 2>/dev/null || true
sleep 2

curl -s http://127.0.0.1:8088/gold-regime-filter | grep -q "GOLD: обязательный regime-фильтр"
curl -s http://127.0.0.1:8088/gold-regime-filter | grep -q "up_impulse_sell_block"
curl -s http://127.0.0.1:8088/gold-regime-filter | grep -q "GOLD_REGIME_FILTER_BACKTEST_STRONG"

echo TEST_UI_GOLD_REGIME_FILTER_STATUS_V1_OK
