# -*- coding: utf-8 -*-
from pathlib import Path
import re

env_file = Path("env/.env.example")

text = env_file.read_text(encoding="utf-8").splitlines()

DESCRIPTIONS = {
    "APP_ENV": "Режим окружения приложения.",
    "PIPE_DEBUG": "Расширенный debug-лог pipeline.",
    "ALLOW_TRADING": "Глобальное разрешение торговли.",

    "EXECUTION_MODE": "Режим исполнения: paper / real_dry_run / real.",
    "RUN_SECS": "Автоостановка pipeline через N секунд. 0 = бесконечно.",

    "FINAM_TOKEN": "Токен доступа Finam API.",
    "FINAM_ACCOUNT_ID": "Торговый account_id Finam.",
    "BROKER_CATEGORY": "Категория клиента у брокера.",
    "ALLOW_SHORT": "Разрешить short-позиции.",

    "SIMULATE_MARKET": "Использовать SimFeed вместо реального market data.",
    "SESSION_OVERRIDE": "Принудительно разрешить торговую сессию.",
    "SESSION_OVERRIDE_LOG_SEC": "Интервал heartbeat-логов override режима.",

    "ENABLE_BROKER_POSITION_SYNC": "Включить синхронизацию позиций брокера.",
    "BROKER_POSITION_SYNC_INTERVAL_SEC": "Интервал sync позиций брокера.",
    "BROKER_POSITION_SYNC_TIMEOUT_SEC": "Timeout broker position sync.",

    "ENABLE_BROKER_OPEN_ORDERS_SYNC": "Включить sync активных заявок.",
    "BROKER_OPEN_ORDERS_SYNC_INTERVAL_SEC": "Интервал sync активных заявок.",

    "DATABASE_URL": "Строка подключения PostgreSQL.",
    "POSTGRES_HOST": "Хост PostgreSQL.",
    "POSTGRES_PORT": "Порт PostgreSQL.",
    "POSTGRES_DB": "Имя БД PostgreSQL.",
    "POSTGRES_USER": "Пользователь PostgreSQL.",
    "POSTGRES_PASSWORD": "Пароль PostgreSQL.",

    "DB_MIN_CONN": "Минимум соединений в пуле.",
    "DB_MAX_CONN": "Максимум соединений в пуле.",

    "ENABLE_TELEGRAM_NOTIFIER": "Включить Telegram уведомления.",
    "TG_BOT_TOKEN": "Telegram bot token.",
    "TG_CHAT_ID": "Telegram chat_id.",

    "ENABLE_EXECUTION_DISPATCHER": "Включить ExecutionDispatcher.",
    "ENABLE_EXECUTION_DISPATCHER_LIVE_ROUTE": "Разрешить live route dispatcher.",
    "ENABLE_EXECUTION_DECISION_LAYER": "Включить ExecutionDecision layer.",
    "ENABLE_PAPER_FILLS": "Разрешить paper fills.",
    "ENABLE_ORDER_ROUTER": "Включить OrderRouter.",
    "ENABLE_OCO_ORDER_MANAGER": "Включить OCO order manager.",
    "EXIT_ON_FILL": "Остановить pipeline после первого fill.",

    "RISK_SOFT": "Soft risk mode без hard-block.",
    "DAILY_LOSS_LIMIT": "Максимальный дневной убыток.",
    "MAX_RISK_PER_TRADE": "Максимальный риск на одну сделку.",
    "CORRELATION_THRESHOLD": "Порог корреляции инструментов.",

    "ENABLE_BROKER_RECONCILIATION_GATE": "Включить reconciliation gate.",
    "ENABLE_BROKER_POSITION_HARD_GATE": "Включить hard gate позиций.",
    "ENABLE_BROKER_PROTECTION_GATE": "Включить protection gate.",

    "BROKER_RECONCILIATION_QTY_TOLERANCE": "Допустимое расхождение qty.",
    "BROKER_POSITION_HARD_GATE_QTY_TOLERANCE": "Tolerance hard gate qty.",

    "ATR_MIN_PCT": "Минимальный ATR % для торговли.",
    "TREND_STRENGTH_MIN": "Минимальная сила тренда.",
    "IMPULSE_MIN": "Минимальный импульс цены.",

    "ENABLE_FILTER_ENGINE": "Включить filter engine.",
    "ENABLE_ML": "Включить ML layer.",

    "SIGNAL_DEDUP_TTL": "TTL дедупликации сигналов.",
    "BREAKOUT_DEDUP_TTL": "TTL дедупликации breakout.",
    "POSITION_INTENT_BLOCK_HEARTBEAT_SEC": "Heartbeat блокировки intent.",

    "PYRAMIDING_THRESHOLD": "Минимальная прибыль для pyramiding.",

    "ENABLE_BR_CONSERVATIVE_BREAKOUT": "Включить BR breakout strategy.",
    "BR_BREAKOUT_SYMBOL": "Символ breakout стратегии.",
    "BR_BREAKOUT_QTY": "Размер позиции breakout.",

    "BR_VOLUME_LOOKBACK": "Lookback объёма.",
    "BR_VOLUME_CONFIRM_RATIO": "Коэффициент подтверждения объёма.",
    "BR_VOLUME_BUFFER_MAX": "Максимальный volume buffer.",

    "NG_SYMBOL": "Основной контракт Natural Gas.",

    "BARS_DB": "SQLite/Postgres storage bars.",
    "BARS_TABLE": "Таблица исторических баров.",
    "BACKTEST_OUTDIR": "Каталог результатов backtest.",
    "CHUNK_MINUTES": "Размер chunk replay/backtest.",

    "COMMISSION": "Комиссия брокера.",
    "COMMISSION_PER_TRADE": "Фиксированная комиссия.",
    "DEFAULT_SLIPPAGE": "Проскальзывание исполнения.",

    "FORCE_ONCE_BUY": "Принудительный тестовый BUY signal.",
    "DRY_RUN": "Dry-run execution mode.",

    "ENABLE_BROKER_POSITION_APPLY_TO_PM": "Разрешить broker→PM sync.",
    "ALLOW_PORTFOLIO_REPAIR": "Разрешить repair portfolio state.",

    "ENABLE_MARKET_RADAR": "Включить Market Radar.",
    "MARKET_RADAR_INTERVAL_SEC": "Интервал Market Radar.",

    "WATCHLIST_MAX_SYMBOLS": "Максимум инструментов watchlist.",

    "LOG_LEVEL": "Уровень логирования.",
    "ENABLE_ORDER_EVENT_STORE": "Включить event store.",

    "ENABLE_AI_LAYER": "Включить AI layer.",
}

result = []

pattern = re.compile(r"^([A-Z0-9_]+)=")

for line in text:
    match = pattern.match(line)

    if match:
        key = match.group(1)
        desc = DESCRIPTIONS.get(key)

        if desc:
            result.append(f"# {desc}")

    result.append(line)

env_file.write_text("\n".join(result) + "\n", encoding="utf-8")

print("ENV_COMMENTS_ENRICHED")
