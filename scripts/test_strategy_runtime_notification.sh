#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/notifications/strategy_runtime_notification.py

python - <<'PY'
from finam_core.notifications.strategy_runtime_notification import (
    StrategyRuntimeNotification,
    StrategyRuntimeNotificationFormatter,
)

event = StrategyRuntimeNotification(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT_M5",
    status="HEALTHY",
    allow_trade=True,
    watch_only=False,
    risk_multiplier=1.2,
    reason="Положительное матожидание: стратегия разрешена и усилена",
)

formatter = StrategyRuntimeNotificationFormatter()

text = formatter.format_telegram(event)
assert "⚙️ Обновлён режим стратегии" in text
assert "Инструмент: BRM6@RTSX" in text
assert "Торговля: разрешена" in text
assert "Риск-мультипликатор: 1.20" in text
assert "Причина: Положительное матожидание" in text

annotation = formatter.format_grafana_annotation(event)
assert annotation["title"] == "Обновлён режим стратегии"
assert "runtime-control" in annotation["tags"]
assert "BR_CONSERVATIVE_BREAKOUT_M5" in annotation["text"]

print("OK: русское уведомление Telegram/Grafana по runtime control формируется")
PY
