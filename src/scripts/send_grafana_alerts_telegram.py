from __future__ import annotations

import json
import os
import subprocess


LOAD_SQL = """
select
    "🕒 Время"::text,
    "📈 Инструмент",
    "🚨 Alert",
    "🧭 Bias",
    "🎯 Уверенность"::text,
    "📝 Причина"
from v_grafana_alerts_ru
order by "🕒 Время" desc
limit 20;
"""

INSERT_SQL = """
insert into telegram_alert_delivery (alert_key, payload)
values (%s, %s::jsonb)
on conflict (alert_key) do nothing
returning id;
"""


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("TELEGRAM_NOT_CONFIGURED")
        return

    subprocess.run(
        [
            "curl",
            "-sS",
            "-X", "POST",
            f"https://api.telegram.org/bot{token}/sendMessage",
            "-d", f"chat_id={chat_id}",
            "-d", f"text={text}",
            "-d", "parse_mode=HTML",
        ],
        check=True,
    )


def main() -> int:
    import psycopg2

    database_url = os.environ["DATABASE_URL"]

    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("TELEGRAM_NOT_CONFIGURED")
        return 0

    sent = 0

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(LOAD_SQL)
            rows = cur.fetchall()

            cooldown_min = int(os.getenv("TELEGRAM_ALERT_COOLDOWN_MIN", "30"))

            cooldown_min = int(os.getenv("TELEGRAM_ALERT_COOLDOWN_MIN", "30"))

            for ts, symbol, alert, bias, confidence, reason in rows:
                # Русский комментарий: cooldown-ключ без timestamp, чтобы не спамить одним и тем же событием.
                alert_key = f"{symbol}|{alert}|{bias}"

                payload = {
                    "ts": ts,
                    "symbol": symbol,
                    "alert": alert,
                    "bias": bias,
                    "confidence": confidence,
                    "reason": reason,
                }

                cur.execute(
                    """
                    select 1
                    from telegram_alert_delivery
                    where alert_key = %s
                      and delivered_at > now() - (%s || ' minutes')::interval
                    limit 1
                    """,
                    (alert_key, cooldown_min),
                )
                if cur.fetchone():
                    continue

                cur.execute(
                    """
                    select 1
                    from telegram_alert_delivery
                    where alert_key = %s
                      and delivered_at > now() - (%s || ' minutes')::interval
                    limit 1
                    """,
                    (alert_key, cooldown_min),
                )
                if cur.fetchone():
                    continue

                cur.execute(
                    INSERT_SQL,
                    (
                        alert_key,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                inserted = cur.fetchone()
                if not inserted:
                    continue

                probability_pct = round(float(confidence or 0) * 100, 1)

                # Русский комментарий: alert bridge не отправляет приказ на сделку.
                # Это только ручная торговая подсказка для анализа.
                side_hint = "LONG" if "LONG" in str(bias) or "НАКОПЛЕНИЕ" in str(alert) else "WAIT"

                entry_hint = "по подтверждению пробоя/удержания уровня"
                stop_hint = "за ближайший локальный уровень отмены сценария"
                take_hint = "не ниже 1.5R–2R от риска"
                qty_hint = "минимальный лот / базовый размер, если риск укладывается в лимит"

                if "ЛОВУШКА" in str(alert) or "FADE" in str(bias):
                    side_hint = "NO_LONG / возможен FADE только вручную"
                    entry_hint = "только после подтверждённого возврата под уровень"
                    stop_hint = "за максимум ложного пробоя"
                    take_hint = "к зоне возврата / ближайшей поддержке"
                    qty_hint = "уменьшенный размер 0.25x–0.5x"

                message = (
                    f"🚨 <b>Finam Core Alert</b>\n\n"
                    f"📈 Инструмент: <b>{symbol}</b>\n"
                    f"Событие: <b>{alert}</b>\n"
                    f"🧭 Bias: <b>{bias}</b>\n"
                    f"🎯 Вероятность профита / confidence: <b>{probability_pct}%</b>\n"
                    f"🕒 Время: {ts}\n\n"
                    f"📌 <b>Ручной сценарий</b>\n"
                    f"Направление: <b>{side_hint}</b>\n"
                    f"Вход: {entry_hint}\n"
                    f"Стоп-лосс: {stop_hint}\n"
                    f"Тейк-профит: {take_hint}\n"
                    f"Количество: {qty_hint}\n\n"
                    f"⚠️ Не автосделка. Только сигнал для ручной проверки.\n\n"
                    f"📝 Причина:\n{reason}"
                )

                send_telegram(message)
                sent += 1

        conn.commit()

    print(f"OK: telegram grafana alerts sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
