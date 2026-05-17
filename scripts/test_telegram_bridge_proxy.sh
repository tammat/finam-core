#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/send_grafana_alerts_telegram.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/send_grafana_alerts_telegram.py").read_text(encoding="utf-8")

checks = [
    "TG_PROXY",
    "TELEGRAM_PROXY",
    "--proxy",
    "--connect-timeout",
    "--max-time",
    "TG_CURL_CONNECT_TIMEOUT",
    "TG_CURL_MAX_TIME",
]

for c in checks:
    assert c in text, c

print("OK: Telegram bridge proxy support")
PY
