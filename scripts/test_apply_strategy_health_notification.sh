#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/apply_strategy_health_to_runtime_control.py \
  src/finam_core/notifications/strategy_runtime_notification.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/apply_strategy_health_to_runtime_control.py").read_text(encoding="utf-8")

assert "StrategyRuntimeNotificationFormatter" in text
assert "TELEGRAM_RUNTIME_CONTROL_EVENT" in text
assert "GRAFANA_RUNTIME_CONTROL_ANNOTATION" in text
assert "format_telegram(event)" in text
assert "format_grafana_annotation(event)" in text

print("OK: apply strategy health печатает русские Telegram/Grafana события")
PY
