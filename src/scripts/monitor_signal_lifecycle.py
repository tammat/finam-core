from __future__ import annotations

import os
import json
import requests
import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier
from finam_core.runtime.signal_lifecycle_engine import SignalLifecycleEngine


def normalize_moex_secid(symbol: str) -> str:
    return str(symbol or "").split("@", 1)[0]


def load_moex_last_price(symbol: str) -> float | None:
    secid = normalize_moex_secid(symbol)
    if not secid:
        return None

    url = (
        "https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"securities/{secid}.json"
    )

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        marketdata = data.get("marketdata", {})
        columns = marketdata.get("columns", [])
        rows = marketdata.get("data", [])

        if not columns or not rows:
            return None

        idx = {name: i for i, name in enumerate(columns)}

        for row in rows:
            for key in ("LAST", "MARKETPRICE", "LCURRENTPRICE"):
                if key in idx:
                    value = row[idx[key]]
                    if value is not None:
                        price = float(value)
                        if price > 0:
                            return price
    except Exception:
        return None

    return None


def send_state_message(notifier: TelegramNotifier, row: dict, new_state: str, close_reason: str | None, price: float) -> None:
    symbol = row["symbol"]

    if new_state == "TRIGGERED":
        text = (
            "✅ <b>Вход активирован</b>\n\n"
            f"Инструмент: <b>{symbol}</b>\n"
            f"Цена: {price:.4f}\n"
            f"Вход: {row['entry_price']}\n"
            f"Стоп-лосс: {row['stop_loss']}\n"
            f"Тейк-профит: {row['take_profit']}"
        )
        notifier.send(text)
        return

    if new_state == "CLOSED" and close_reason == "TAKE_PROFIT":
        notifier.send(f"🏁 <b>Тейк-профит достигнут</b>\n\nИнструмент: <b>{symbol}</b>\nЦена: {price:.4f}")
        return

    if new_state == "CLOSED" and close_reason == "STOP_LOSS":
        notifier.send(f"🛑 <b>Стоп-лосс достигнут</b>\n\nИнструмент: <b>{symbol}</b>\nЦена: {price:.4f}")
        return

    if new_state == "EXPIRED":
        notifier.send(f"⌛ <b>Сигнал истёк</b>\n\nИнструмент: <b>{symbol}</b>")
        return


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    limit = int(os.getenv("SIGNAL_LIFECYCLE_MONITOR_LIMIT", "50"))

    conn = psycopg2.connect(dsn)
    notifier = TelegramNotifier()
    engine = SignalLifecycleEngine()

    checked = 0
    updated = 0
    expired = 0
    price_missing = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    signal_id,
                    symbol,
                    strategy,
                    regime,
                    state,
                    entry_price,
                    stop_loss,
                    take_profit,
                    risk_reward,
                    expire_at,
                    raw_json
                from signal_lifecycle
                where state in ('NEW','ACTIVE','TRIGGERED')
                order by created_at asc
                limit %s
                """,
                (limit,),
            )

            rows = []
            for r in cur.fetchall():
                rows.append({
                    "id": int(r[0]),
                    "signal_id": str(r[1]),
                    "symbol": str(r[2]),
                    "strategy": str(r[3] or ""),
                    "regime": str(r[4] or ""),
                    "state": str(r[5]),
                    "entry_price": float(r[6] or 0),
                    "stop_loss": float(r[7] or 0),
                    "take_profit": float(r[8] or 0),
                    "risk_reward": float(r[9] or 0),
                    "expire_at": r[10],
                    "raw_json": r[11] or {},
                })

            for row in rows:
                checked += 1

                cur.execute(
                    """
                    select case when expire_at is not null and expire_at <= now() then true else false end
                    from signal_lifecycle
                    where id = %s
                    """,
                    (row["id"],),
                )
                is_expired = bool(cur.fetchone()[0])

                if is_expired:
                    cur.execute(
                        """
                        update signal_lifecycle
                        set state = 'EXPIRED',
                            closed_at = now(),
                            close_reason = 'TIME_EXPIRED'
                        where id = %s
                          and state in ('NEW','ACTIVE','TRIGGERED')
                        """,
                        (row["id"],),
                    )
                    if cur.rowcount:
                        expired += 1
                        updated += 1
                        send_state_message(notifier, row, "EXPIRED", "TIME_EXPIRED", 0.0)
                    continue

                price = load_moex_last_price(row["symbol"])
                if price is None:
                    price_missing += 1
                    continue

                decision = engine.evaluate(
                    state=row["state"],
                    current_price=price,
                    entry_price=row["entry_price"],
                    stop_loss=row["stop_loss"],
                    take_profit=row["take_profit"],
                )

                if decision.state == row["state"]:
                    continue

                if decision.state == "TRIGGERED":
                    cur.execute(
                        """
                        update signal_lifecycle
                        set state = 'TRIGGERED',
                            triggered_at = coalesce(triggered_at, now())
                        where id = %s
                          and state in ('NEW','ACTIVE')
                        """,
                        (row["id"],),
                    )

                elif decision.state == "ACTIVE":
                    cur.execute(
                        """
                        update signal_lifecycle
                        set state = 'ACTIVE',
                            activated_at = coalesce(activated_at, now())
                        where id = %s
                          and state = 'NEW'
                        """,
                        (row["id"],),
                    )

                elif decision.state == "CLOSED":
                    cur.execute(
                        """
                        update signal_lifecycle
                        set state = 'CLOSED',
                            closed_at = now(),
                            close_reason = %s
                        where id = %s
                          and state = 'TRIGGERED'
                        """,
                        (decision.close_reason, row["id"]),
                    )
                else:
                    continue

                if cur.rowcount:
                    updated += 1
                    send_state_message(notifier, row, decision.state, decision.close_reason, price)

    print(
        "SIGNAL_LIFECYCLE_MONITOR_OK "
        f"checked={checked} updated={updated} expired={expired} price_missing={price_missing}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
