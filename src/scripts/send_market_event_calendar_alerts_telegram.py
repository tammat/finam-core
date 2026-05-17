from __future__ import annotations

import json
import os
import subprocess

import psycopg2


SQL = """
select
    "🕒 Время события"::text,
    "📈 Группа инструментов",
    "🚨 Событие",
    "📝 Описание",
    "⚠️ Важность",
    "⏳ Минут до события",
    "🎛 Режим исполнения"
from v_market_event_calendar_alerts_ru
where "🎛 Режим исполнения" in ('⚠️ REDUCE', '⛔ BLOCK')
order by "🕒 Время события" asc
limit 20;
"""

INSERT_SQL = """
insert into telegram_alert_delivery (alert_key, payload)
values (%s, %s::jsonb)
on conflict (alert_key) do nothing
returning id;
"""


def send_telegram(text: str) -> bool:
    token = (
        os.getenv("TG_ALERT_BOT_TOKEN")
        or os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("TG_BOT_TOKEN")
    )
    chat_id = (
        os.getenv("TG_ALERT_CHAT")
        or os.getenv("TELEGRAM_CHAT_ID")
        or os.getenv("TG_CHAT_ID")
    )

    if not token or not chat_id:
        print("TELEGRAM_NOT_CONFIGURED")
        return False

    cmd = [
        "curl",
        "-sS",
        "--connect-timeout", os.getenv("TG_CURL_CONNECT_TIMEOUT", "10"),
        "--max-time", os.getenv("TG_CURL_MAX_TIME", "30"),
    ]

    proxy = os.getenv("TG_PROXY") or os.getenv("TELEGRAM_PROXY")
    if proxy:
        cmd.extend(["--proxy", proxy])

    cmd.extend([
        "-X", "POST",
        f"https://api.telegram.org/bot{token}/sendMessage",
        "-d", f"chat_id={chat_id}",
        "-d", f"text={text}",
        "-d", "parse_mode=HTML",
    ])

    result = subprocess.run(cmd, text=True, capture_output=True, check=False)

    if result.returncode != 0:
        print(f"TELEGRAM_SEND_FAILED returncode={result.returncode} stderr={result.stderr}")
        return False

    if '"ok":true' not in result.stdout:
        print(f"TELEGRAM_SEND_FAILED response={result.stdout}")
        return False

    return True


def main() -> int:
    database_url = os.environ["DATABASE_URL"]
    sent = 0

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

            for (
                event_time,
                group,
                event,
                description,
                severity,
                minutes_to_event,
                execution_mode,
            ) in rows:
                alert_key = f"market_event|{event_time}|{group}|{event}|{execution_mode}"

                payload = {
                    "event_time": event_time,
                    "instrument_group": group,
                    "event": event,
                    "description": description,
                    "severity": severity,
                    "minutes_to_event": minutes_to_event,
                    "execution_mode": execution_mode,
                }

                if execution_mode == "⛔ BLOCK":
                    action_text = "⛔ Входы по связанным стратегиям временно запрещены."
                else:
                    action_text = "⚠️ Размер позиции по связанным стратегиям должен быть снижен."

                message = (
                    f"📅 <b>Календарное событие рынка</b>\n\n"
                    f"🚨 Событие: <b>{event}</b>\n"
                    f"📈 Группа инструментов: <b>{group}</b>\n"
                    f"⚠️ Важность: <b>{severity}</b>\n"
                    f"⏳ До события: <b>{minutes_to_event} мин.</b>\n"
                    f"🎛 Режим исполнения: <b>{execution_mode}</b>\n\n"
                    f"{action_text}\n\n"
                    f"🕒 Время события: {event_time}\n"
                    f"📝 Описание: {description}"
                )

                if not send_telegram(message):
                    continue

                cur.execute(
                    INSERT_SQL,
                    (
                        alert_key,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                if cur.fetchone():
                    sent += 1

        conn.commit()

    print(f"OK: market event telegram alerts sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
