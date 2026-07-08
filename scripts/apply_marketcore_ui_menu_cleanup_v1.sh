#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_MARKETCORE_UI_MENU_CLEANUP_V1 ==="

python - <<'PY'
from pathlib import Path
import re

forbidden = [
    "/paper-sample-accumulation-monitor",
    "/paper-edge-discovery",
    "/paper-edge-market-data-binding",
    "/paper-edge-market-symbol-alias-plan",
    "/paper-edge-market-data-freshness",
    "/edge-oos-validation",
    "/edge-oos-backtest",
    "/micro-live-readiness",
    "/orders",
]

for path in [
    Path("src/marketcore/presentation/route_groups.py"),
    Path("src/marketcore/presentation/ui_labels.py"),
]:
    s = path.read_text(encoding="utf-8")

    for route in forbidden:
        s = re.sub(rf'\n\s*"{re.escape(route)}"\s*,', "", s)
        s = re.sub(rf'\n\s*"{re.escape(route)}"\s*:\s*"[^"]*"\s*,', "", s)

    s = s.replace('"Edge Factory"', '"Фабрика Edge"')
    s = s.replace('"Discovery"', '"Поиск"')
    s = s.replace('"Runtime"', '"Наблюдение"')
    s = s.replace('"Paper"', '"Тестовый контур"')
    s = s.replace('"Worker"', '"Обработчик"')
    s = s.replace('"Orders"', '"Заявки"')

    path.write_text(s, encoding="utf-8")

print("patch_status=applied")
PY

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_menu_cleanup PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/registry_autodiscovery.py

echo "VERDICT=MARKETCORE_UI_MENU_CLEANUP_V1_PATCH_READY"
