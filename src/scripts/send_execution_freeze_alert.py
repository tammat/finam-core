# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


MSK = ZoneInfo("Europe/Moscow")
FREEZE_MINUTES = int(os.getenv("EXECUTION_FREEZE_MINUTES", "120"))
DEDUP_MINUTES = int(os.getenv("EXECUTION_FREEZE_DEDUP_MINUTES", "180"))


def is_trading_window(now: datetime) -> bool:
    # Русский комментарий: пока грубое окно Мосбиржи; позже заменим на календарь торговых сессий.
    if now.weekday() >= 5:
        return False
    return time(10, 0) <= now.time() <= time(23, 50)


def main() -> None:
    now = datetime.now(MSK)

    if not is_trading_window(now):
        print("EXECUTION_FREEZE_ALERT_SKIP reason=not_trading_window", flush=True)
        return

    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "finam_core"),
        user=os.getenv("PGUSER") or None,
        host=os.getenv("PGHOST") or None,
        port=os.getenv("PGPORT") or None,
        password=os.getenv("PGPASSWORD") or None,
    )

    with conn.cursor() as cur:
        cur.execute("""
            SELECT MAX(ts)
            FROM trades
            WHERE COALESCE(raw_json->>'paper_only', payload->>'paper_only') = 'true'
               OR payload->>'paper_only' = 'true'
               OR raw_json->>'paper_only' = 'true';
        """)
        last_trade_ts = cur.fetchone()[0]

    if last_trade_ts is None:
        age_minutes = None
        frozen = True
    else:
        age_minutes = (now - last_trade_ts.astimezone(MSK)).total_seconds() / 60.0
        frozen = age_minutes > FREEZE_MINUTES

    if not frozen:
        print(f"EXECUTION_FREEZE_ALERT_OK age_minutes={round(age_minutes or 0, 1)}", flush=True)
        return

    alert_key = "execution_freeze:paper_trades"

    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM runtime_alert_dedup
            WHERE alert_key = %s
              AND last_sent_at > now() - (%s || ' minutes')::interval
        """, (alert_key, DEDUP_MINUTES))
        already_sent = cur.fetchone() is not None

    if already_sent:
        print("EXECUTION_FREEZE_ALERT_DEDUP_SKIP", flush=True)
        return

    text = "\n".join([
        "🧊 Execution Freeze Alert",
        "",
        "Новые paper-сделки давно не появлялись.",
        f"Порог: {FREEZE_MINUTES} минут",
        f"Последняя сделка: {last_trade_ts}",
        f"Возраст, минут: {round(age_minutes, 1) if age_minutes is not None else 'NO_DATA'}",
        "",
        "Проверь: market data, session gate, strategy signals, risk/runtime-control.",
    ])

    TelegramNotifier().send(text)

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO runtime_alert_dedup (alert_key, last_sent_at, payload)
            VALUES (%s, now(), %s::jsonb)
            ON CONFLICT (alert_key) DO UPDATE SET
                last_sent_at = now(),
                payload = EXCLUDED.payload
        """, (
            alert_key,
            json.dumps({
                "last_trade_ts": str(last_trade_ts),
                "age_minutes": age_minutes,
                "threshold_minutes": FREEZE_MINUTES,
                "source": "execution_freeze_alert",
            }, ensure_ascii=False),
        ))

    conn.commit()

    print("EXECUTION_FREEZE_ALERT_SENT", flush=True)


if __name__ == "__main__":
    main()
