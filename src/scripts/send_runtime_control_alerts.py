# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


ALERT_STATUSES = {"DEGRADED", "BLOCKED", "CRITICAL"}
DEDUP_MINUTES = int(os.getenv("RUNTIME_ALERT_DEDUP_MINUTES", "180"))


def main() -> None:
    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "finam_core"),
        user=os.getenv("PGUSER") or None,
        host=os.getenv("PGHOST") or None,
        port=os.getenv("PGPORT") or None,
        password=os.getenv("PGPASSWORD") or None,
    )

    with conn.cursor() as cur:
        cur.execute("""
            SELECT symbol, strategy, status, allow_trade, watch_only,
                   risk_multiplier, reason, updated_at
            FROM strategy_runtime_control
            WHERE status = ANY(%s)
               OR allow_trade = false
               OR watch_only = true
               OR risk_multiplier < 1
            ORDER BY updated_at DESC;
        """, (list(ALERT_STATUSES),))
        rows = cur.fetchall()

    sent = 0

    for row in rows:
        symbol, strategy, status, allow_trade, watch_only, risk_x, reason, updated_at = row
        alert_key = f"runtime:{symbol}:{strategy}:{status}:{allow_trade}:{watch_only}:{risk_x}:{reason}"

        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM runtime_alert_dedup
                WHERE alert_key = %s
                  AND last_sent_at > now() - (%s || ' minutes')::interval
            """, (alert_key, DEDUP_MINUTES))
            already_sent = cur.fetchone() is not None

        if already_sent:
            continue

        text = "\n".join([
            "⚠️ Runtime Control Alert",
            "",
            f"Инструмент: {symbol}",
            f"Стратегия: {strategy}",
            f"Статус: {status}",
            f"Торговля разрешена: {allow_trade}",
            f"Watch-only: {watch_only}",
            f"Risk x: {risk_x}",
            f"Причина: {reason}",
            f"Обновлено: {updated_at}",
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
                    "symbol": symbol,
                    "strategy": strategy,
                    "status": status,
                    "allow_trade": allow_trade,
                    "watch_only": watch_only,
                    "risk_multiplier": float(risk_x or 0.0),
                    "reason": reason,
                    "updated_at": str(updated_at),
                }, ensure_ascii=False),
            ))
        conn.commit()
        sent += 1

    print(f"RUNTIME_CONTROL_ALERTS_OK sent={sent}", flush=True)


if __name__ == "__main__":
    main()
