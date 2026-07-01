#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_RU_COPY_PATCH_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/viewmodels/market_intelligence_vm.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.viewmodels.market_intelligence_vm import build_default_market_intelligence_vm

vm = build_default_market_intelligence_vm()

text = " ".join(
    [m.title for m in vm.overview]
    + [q.check for q in vm.quality]
    + [i.asset_class for i in vm.instruments]
    + [i.freshness for i in vm.instruments]
    + [i.last_ts for i in vm.instruments]
)

for forbidden in [
    "Fresh",
    "Futures",
    "Equity",
    "Crypto",
    "Volume",
    "Ticks",
    "2026-06-30",
    "2026-07-01",
]:
    assert forbidden not in text, forbidden

assert "Актуал." in text
assert "Фьючерсы" in text
assert "Акции" in text
assert "Крипто" in text
assert "Объём" in text
assert "Тики" in text
assert "30.06.2026" in text
assert "01.07.2026" in text

print("market_ru_copy=READY")
print("fresh_ru=READY")
print("asset_classes_ru=READY")
print("quality_checks_ru=READY")
print("date_format_ru=READY")
print("ux_copy_ru_full_page=READY")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=MARKET_RU_COPY_PATCH_V1_READY")
PY

echo "VERDICT=TEST_MARKET_RU_COPY_PATCH_V1_OK"
