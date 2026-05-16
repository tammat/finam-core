#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_grafana_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/send_grafana_alerts_telegram.py").read_text(encoding="utf-8")

checks = [
    "TELEGRAM_ALERT_COOLDOWN_MIN",
    "delivered_at > now()",
    "cooldown_min",
    'alert_key = f"{symbol}|{alert}|{bias}"',
]

for c in checks:
    assert c in text, c

print("OK: Telegram alert cooldown layer")
PY
