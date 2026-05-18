from __future__ import annotations

import json
import os
import psycopg2
import requests
from datetime import datetime, timezone

from finam_core.notifications.telegram_notifier import TelegramNotifier


def load_watch_candidates(cur, limit: int = 10) -> list[dict]:
    cur.execute(
        """
        select
            id,
            symbol,
            strategy,
            regime,
            score,
            reason,
            raw_json
        from radar_candidate_analysis
        where decision = 'WATCH'
        order by created_at desc, id desc
        limit %s
        """,
        (limit,),
    )

    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "analysis_id": int(r[0]),
                "symbol": str(r[1]),
                "strategy": str(r[2] or "UNKNOWN"),
                "regime": str(r[3] or "UNKNOWN"),
                "score": float(r[4] or 0.0),
                "reason": str(r[5] or ""),
                "raw_json": r[6] or {},
            }
        )
    return rows



def normalize_moex_secid(symbol: str) -> str:
    """Русский комментарий: LKOH@MISX -> LKOH."""
    return str(symbol or "").split("@", 1)[0]


def load_moex_last_price(symbol: str) -> float | None:
    """Русский комментарий: получает последнюю цену акции с MOEX ISS."""
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
            # Русский комментарий: предпочитаем LAST, fallback на MARKETPRICE / LCURRENTPRICE.
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


def build_trade_setup(candidate: dict, price: float) -> dict:
    """Русский комментарий: строит entry/stop/take по типу стратегии."""
    strategy = str(candidate.get("strategy") or "").upper()
    regime = str(candidate.get("regime") or "")

    if price <= 0:
        return {
            "decision": "WATCH",
            "reason": "цена недоступна",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    if "MEAN_REVERSION" in strategy or "OVERSOLD" in regime.upper():
        entry = price
        stop = price * 0.970
        take = price * 1.025
        setup_name = "отскок после снижения"
    elif "BREAKOUT" in strategy or "TREND" in regime.upper():
        entry = price * 1.002
        stop = price * 0.985
        take = price * 1.035
        setup_name = "пробой / продолжение импульса"
    else:
        entry = price
        stop = price * 0.980
        take = price * 1.030
        setup_name = "универсальный сетап наблюдения"

    risk = abs(entry - stop)
    reward = abs(take - entry)
    rr = reward / risk if risk > 0 else 0.0

    if rr >= 1.5:
        decision = "ALERT"
    else:
        decision = "WATCH"

    return {
        "decision": decision,
        "reason": f"{setup_name}; price={price:.4f}; rr={rr:.2f}",
        "entry_price": round(entry, 4),
        "stop_loss": round(stop, 4),
        "take_profit": round(take, 4),
        "risk_reward": round(rr, 4),
    }

def make_runtime_decision(candidate: dict) -> dict:
    """Русский комментарий: получает реальную цену MOEX и строит strategy-specific setup."""
    score = float(candidate.get("score") or 0.0)
    strategy = str(candidate.get("strategy") or "UNKNOWN")

    if score <= 0:
        return {
            "decision": "IGNORE",
            "reason": "нулевой score после runtime-проверки",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    if strategy == "UNKNOWN":
        return {
            "decision": "WATCH",
            "reason": "нет стратегии; оставлен в наблюдении",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    price = load_moex_last_price(candidate["symbol"])

    if price is None:
        return {
            "decision": "WATCH",
            "reason": "MOEX цена недоступна; оставлен в наблюдении",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    return build_trade_setup(candidate, price)


def save_runtime_analysis(cur, candidate: dict, decision: dict) -> None:
    payload = {
        "source_analysis_id": candidate["analysis_id"],
        "candidate": candidate,
        "runtime_decision": decision,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    cur.execute(
        """
        insert into radar_candidate_analysis (
            symbol,
            source,
            decision,
            reason,
            strategy,
            regime,
            entry_price,
            stop_loss,
            take_profit,
            risk_reward,
            score,
            raw_json
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        """,
        (
            candidate["symbol"],
            "watch_candidate_runtime_analyzer",
            decision["decision"],
            decision["reason"],
            candidate["strategy"],
            candidate["regime"],
            decision["entry_price"],
            decision["stop_loss"],
            decision["take_profit"],
            decision["risk_reward"],
            candidate["score"],
            json.dumps(payload, ensure_ascii=False, default=str),
        ),
    )


def send_alert_if_any(notifier: TelegramNotifier, candidate: dict, decision: dict) -> int:
    if decision["decision"] != "ALERT":
        return 0

    text = (
        "🚨 Торговый ALERT\n\n"
        f"Инструмент: {candidate['symbol']}\n"
        f"Стратегия: {candidate['strategy']}\n"
        f"Режим: {candidate['regime']}\n\n"
        f"Точка входа: {decision['entry_price']}\n"
        f"Стоп-лосс: {decision['stop_loss']}\n"
        f"Тейк-профит: {decision['take_profit']}\n"
        f"Risk/Reward: {decision['risk_reward']}\n\n"
        f"Причина: {decision['reason']}"
    )

    notifier.send(text)
    return 1


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    limit = int(os.getenv("WATCH_RUNTIME_LIMIT", "10"))

    conn = psycopg2.connect(dsn)
    notifier = TelegramNotifier()

    processed = 0
    alerts = 0

    with conn:
        with conn.cursor() as cur:
            candidates = load_watch_candidates(cur, limit=limit)

            for candidate in candidates:
                decision = make_runtime_decision(candidate)
                save_runtime_analysis(cur, candidate, decision)
                alerts += send_alert_if_any(notifier, candidate, decision)
                processed += 1

    print(
        f"WATCH_CANDIDATE_RUNTIME_ANALYSIS_OK processed={processed} alerts={alerts}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
