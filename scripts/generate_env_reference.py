# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENV_PATTERN = re.compile(r'os\.getenv\(\s*[\'"]([A-Z0-9_]+)[\'"]')

DESCRIPTIONS = {
    "DATABASE_URL": "Строка подключения к PostgreSQL.",
    "FINAM_TOKEN": "Токен доступа к API Финама.",
    "FINAM_ACCOUNT_ID": "Идентификатор торгового счёта Финама.",
    "EXECUTION_MODE": "Режим исполнения: paper, real_dry_run или real.",
    "RISK_SOFT": "Мягкий режим риска: логировать риск без жёсткой остановки.",
    "FORCE_ONCE_BUY": "Тестовый режим: принудительно создать один BUY-сигнал.",
    "PIPE_DEBUG": "Включить подробные debug-логи pipeline.",
    "SESSION_OVERRIDE": "Игнорировать торговую сессию для тестов.",
    "SIMULATE_MARKET": "Использовать симулятор рыночных данных.",
    "RUN_SECS": "Сколько секунд работает тестовый pipeline.",
    "SESSION_OVERRIDE_LOG_SEC": "Интервал heartbeat-логов SESSION_OVERRIDE.",
    "EXIT_ON_FILL": "Завершать pipeline после fill.",
    "ENABLE_PAPER_FILLS": "Разрешить paper-fill исполнение.",
    "ENABLE_TELEGRAM_NOTIFIER": "Включить Telegram-уведомления.",
    "TG_BOT_TOKEN": "Токен Telegram-бота.",
    "TG_CHAT_ID": "ID Telegram-чата.",
    "ATR_MIN_PCT": "Минимальная волатильность ATR для входа.",
    "TREND_STRENGTH_MIN": "Минимальная сила тренда.",
    "IMPULSE_MIN": "Минимальный импульс цены.",
    "SIGNAL_DEDUP_TTL": "TTL дедупликации сигналов.",
    "BREAKOUT_DEDUP_TTL": "TTL дедупликации breakout-сигналов.",
    "PYRAMIDING_THRESHOLD": "Порог прибыли для добавления к позиции.",
    "MAX_PORTFOLIO_HEAT": "Максимальная доля риска/экспозиции портфеля.",
    "MAX_SYMBOL_HEAT": "Максимальная доля риска по одному инструменту.",
    "MAX_MARGIN_UTILIZATION": "Максимальная загрузка ГО/маржи.",
    "MAX_DAILY_LOSS_PCT": "Максимальный дневной убыток.",
    "MAX_DRAWDOWN_PCT": "Максимальная просадка.",
}

found = set()

for path in ROOT.rglob("*.py"):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        continue
    found.update(ENV_PATTERN.findall(text))

lines = [
    "# Описание параметров .env Finam_Core",
    "",
    "| Параметр | Описание |",
    "|---|---|",
]

for key in sorted(found):
    lines.append(f"| `{key}` | {DESCRIPTIONS.get(key, 'Требуется уточнить описание по месту использования в коде.')} |")

out = ROOT / "docs" / "ENV_REFERENCE_RU.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"ENV_REFERENCE_CREATED {out}")
