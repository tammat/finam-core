from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


STATE_FILE = Path("runtime_state/br_forward_accumulation_state.json")

SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"

PROFILE = "BR_ASIA_SCALP_MEDIUM_MOVE"


def load_previous_state() -> dict:
    if not STATE_FILE.exists():
        return {}

    return json.loads(STATE_FILE.read_text())


def save_state(payload: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def classify_status(
    *,
    pf: float,
    expectancy: float,
    repeatability_confirmed: bool,
    contamination: str,
) -> str:

    if not repeatability_confirmed:
        return "RESEARCH_WATCH"

    if contamination == "HIGH_DAY_CONCENTRATION":
        return "CONTAMINATED"

    if pf >= 1.20 and expectancy > 0:
        return "IMPROVING"

    if pf >= 1.00:
        return "STABLE"

    return "DEGRADING"


def build_message(old_status: str, new_status: str, payload: dict) -> str:
    return (
        "📊 Изменение статуса стратегии BR\n"
        f"Инструмент: {payload['symbol']}\n"
        f"Стратегия: {payload['strategy']}\n"
        f"Таймфрейм: {payload['timeframe']}\n"
        f"Статус: {old_status} → {new_status}\n"
        f"Сделок: {payload['trades']}\n"
        f"Profit Factor: {payload['pf']:.6f}\n"
        f"Ожидание на сделку: {payload['expectancy']:.6f}\n"
        f"Повторяемость подтверждена: {'да' if payload['repeatability_confirmed'] else 'нет'}\n"
        f"Концентрация/загрязнение выборки: {payload['contamination']}\n"
        "Решение: runtime не включается, стратегия остаётся в research-watch.\n"
    )


def build_profile_message(old_status: str, new_status: str, payload: dict) -> str:
    return (
        "📊 Изменение статуса research-профиля BR\n"
        f"Профиль: {payload['profile']}\n"
        f"Источник: {payload['source_strategy']}\n"
        f"Статус: {old_status} → {new_status}\n"
        f"Сделок: {payload['trades']}\n"
        f"Дней: {payload['days']}\n"
        f"Profit Factor: {payload['pf']:.6f}\n"
        f"Ожидание на сделку: {payload['expectancy']:.6f}\n"
        f"Repeatability: {payload['repeatability_status']}\n"
        f"Top-day contribution: {payload['top_day_contribution']:.6f}\n"
        "Решение: runtime не включается, профиль остаётся в forward accumulation.\n"
    )


def send_telegram(message: str) -> None:
    # Русский комментарий: используем единый TG_AI_TOKEN, отдельный TELEGRAM_BOT_TOKEN не плодим.
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TG_AI_TOKEN", "")
    # Русский комментарий: для канала статусов стратегий приоритетно используем отдельный chat_id канала.
    chat_id = os.environ.get("TG_STRATEGY_STATUS_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")
    proxy = os.environ.get("TELEGRAM_PROXY") or os.environ.get("TG_PROXY", "")

    if not token or not chat_id:
        print("TELEGRAM_DISABLED")
        return

    import requests

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Русский комментарий: защищаемся от ошибочно склеенных строк .env.
    for marker in ("TG_STRATEGY_STATUS_CHAT_ID=", "TELEGRAM_CHAT_ID=", "\n", "\r"):
        if marker in proxy:
            proxy = proxy.split(marker, 1)[0].strip()

    proxies = {"http": proxy, "https": proxy} if proxy else None

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
        },
        timeout=15,
        proxies=proxies,
    )

    print(
        f"TELEGRAM_NOTIFY status_code={response.status_code} body={response.text[:300]}",
        flush=True,
    )


def classify_profile_status(*, days: int, pf: float, expectancy: float, top_day_contribution: float) -> str:
    if days < 3:
        return "PROFILE_WATCH_TOO_FEW_DAYS"
    if top_day_contribution >= 0.80:
        return "PROFILE_WATCH_CONCENTRATED"
    if pf >= 1.20 and expectancy > 0:
        return "PROFILE_REPEATABILITY_CANDIDATE"
    if pf >= 1.00 and expectancy > 0:
        return "PROFILE_WATCH"
    return "PROFILE_DEGRADING"


def build_profile_payload(database_url: str) -> dict:
    sql = """
    WITH fs AS (
        SELECT
            symbol,
            timeframe,
            ts,
            close,
            LAG(close) OVER (
                PARTITION BY symbol, timeframe
                ORDER BY ts
            ) AS prev_close
        FROM feature_snapshots
        WHERE symbol = %(symbol)s
          AND timeframe = 'M5'
    ),
    base AS (
        SELECT
            tcs.closed_trade_id,
            COALESCE(tcs.exit_ts, tcs.entry_ts) AS trade_ts,
            a.pnl
        FROM trade_context_snapshots tcs
        JOIN trade_attribution_v2 a
          ON a.closed_trade_id = tcs.closed_trade_id
        WHERE tcs.symbol = %(symbol)s
          AND tcs.strategy = %(strategy)s
          AND a.strategy = %(strategy)s
          AND tcs.context_quality = 'FULL'
          AND tcs.regime = 'LOW_IMPULSE'
          AND tcs.trend = 'down'
          AND tcs.volatility = 'high'
          AND EXTRACT(EPOCH FROM (tcs.exit_ts - tcs.entry_ts)) / 60.0 < 5
          AND tcs.entry_ts IS NOT NULL
          AND tcs.exit_ts IS NOT NULL
          AND EXTRACT(HOUR FROM COALESCE(tcs.exit_ts, tcs.entry_ts)) >= 0
          AND EXTRACT(HOUR FROM COALESCE(tcs.exit_ts, tcs.entry_ts)) < 10
    ),
    profile_rows AS (
        SELECT
            b.trade_ts::date AS trade_day,
            b.pnl
        FROM base b
        JOIN LATERAL (
            SELECT *
            FROM fs
            WHERE fs.ts <= b.trade_ts
              AND fs.prev_close IS NOT NULL
            ORDER BY fs.ts DESC
            LIMIT 1
        ) f ON TRUE
        WHERE
            CASE
                WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
                ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
            END > 0.15
          AND
            CASE
                WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
                ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
            END <= 0.35
    ),
    total AS (
        SELECT
            COUNT(*) AS trades,
            COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0) AS wins,
            COALESCE(SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END), 0) AS losses,
            COALESCE(SUM(pnl), 0) AS net_pnl,
            COALESCE(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 0) AS gross_profit,
            ABS(COALESCE(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END), 0)) AS gross_loss,
            COUNT(DISTINCT trade_day) AS days
        FROM profile_rows
    ),
    day_pnl AS (
        SELECT
            trade_day,
            SUM(pnl) AS day_net_pnl
        FROM profile_rows
        GROUP BY trade_day
    )
    SELECT
        total.trades,
        total.wins,
        total.losses,
        total.net_pnl,
        total.gross_profit,
        total.gross_loss,
        total.days,
        COALESCE(MAX(day_pnl.day_net_pnl), 0) AS top_day_pnl
    FROM total
    LEFT JOIN day_pnl ON TRUE
    GROUP BY
        total.trades,
        total.wins,
        total.losses,
        total.net_pnl,
        total.gross_profit,
        total.gross_loss,
        total.days;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"symbol": SYMBOL, "strategy": STRATEGY})
            row = cur.fetchone()

    trades = int(row[0] or 0)
    wins = int(row[1] or 0)
    losses = int(row[2] or 0)
    net_pnl = float(row[3] or 0.0)
    gross_profit = float(row[4] or 0.0)
    gross_loss = float(row[5] or 0.0)
    days = int(row[6] or 0)
    top_day_pnl = float(row[7] or 0.0)

    pf = gross_profit / gross_loss if gross_loss else 0.0
    expectancy = net_pnl / trades if trades else 0.0
    top_day_contribution = top_day_pnl / net_pnl if net_pnl else 0.0

    status = classify_profile_status(
        days=days,
        pf=pf,
        expectancy=expectancy,
        top_day_contribution=top_day_contribution,
    )

    if days < 3:
        repeatability_status = "too_few_days"
    elif top_day_contribution >= 0.80:
        repeatability_status = "high_day_concentration"
    elif pf >= 1.20 and expectancy > 0:
        repeatability_status = "candidate"
    else:
        repeatability_status = "not_confirmed"

    return {
        "profile": PROFILE,
        "source_strategy": STRATEGY,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "days": days,
        "net_pnl": net_pnl,
        "pf": pf,
        "expectancy": expectancy,
        "top_day_contribution": top_day_contribution,
        "repeatability_status": repeatability_status,
        "status": status,
        "runtime_enabled": False,
    }


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql_stats = """
    SELECT
        trades,
        profit_factor,
        expectancy
    FROM strategy_statistics_v2
    WHERE symbol=%(symbol)s
      AND strategy=%(strategy)s
      AND timeframe=%(timeframe)s
      AND trade_source='paper'
    ORDER BY calculated_at DESC
    LIMIT 1;
    """

    sql_repeatability = """
    SELECT false AS repeatability_confirmed,
           'HIGH_DAY_CONCENTRATION' AS contamination;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:

            cur.execute(
                sql_stats,
                {
                    "symbol": SYMBOL,
                    "strategy": STRATEGY,
                    "timeframe": TIMEFRAME,
                },
            )

            stats = cur.fetchone()

            cur.execute(sql_repeatability)
            repeatability = cur.fetchone()

    trades = int(stats[0] or 0)
    pf = float(stats[1] or 0.0)
    expectancy = float(stats[2] or 0.0)

    repeatability_confirmed = bool(repeatability[0])
    contamination = str(repeatability[1])

    new_status = classify_status(
        pf=pf,
        expectancy=expectancy,
        repeatability_confirmed=repeatability_confirmed,
        contamination=contamination,
    )

    payload = {
        "symbol": SYMBOL,
        "strategy": STRATEGY,
        "timeframe": TIMEFRAME,
        "trades": trades,
        "pf": pf,
        "expectancy": expectancy,
        "repeatability_confirmed": repeatability_confirmed,
        "contamination": contamination,
        "status": new_status,
    }

    previous = load_previous_state()

    old_status = previous.get("status", "INITIAL")

    print("BR_FORWARD_ACCUMULATION_V1")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print(f"trades={trades}")
    print(f"pf={pf:.6f}")
    print(f"expectancy={expectancy:.6f}")
    print(f"repeatability_confirmed={str(repeatability_confirmed).lower()}")
    print(f"contamination={contamination}")
    print(f"old_status={old_status}")
    print(f"new_status={new_status}")

    if old_status != new_status:
        print(
            f"STATUS_CHANGED old={old_status} new={new_status}",
            flush=True,
        )

        send_telegram(
            build_message(
                old_status=old_status,
                new_status=new_status,
                payload=payload,
            )
        )
    else:
        print("STATUS_UNCHANGED")

    profile_payload = build_profile_payload(database_url)
    old_profile_status = previous.get("profile_status", "INITIAL")
    new_profile_status = profile_payload["status"]

    print("PROFILE_FORWARD_ACCUMULATION")
    print(f"profile={profile_payload['profile']}")
    print(f"trades={profile_payload['trades']}")
    print(f"days={profile_payload['days']}")
    print(f"pf={profile_payload['pf']:.6f}")
    print(f"expectancy={profile_payload['expectancy']:.6f}")
    print(f"top_day_contribution={profile_payload['top_day_contribution']:.6f}")
    print(f"old_profile_status={old_profile_status}")
    print(f"new_profile_status={new_profile_status}")

    if old_profile_status != new_profile_status:
        print(
            f"PROFILE_STATUS_CHANGED old={old_profile_status} new={new_profile_status}",
            flush=True,
        )
        send_telegram(
            build_profile_message(
                old_status=old_profile_status,
                new_status=new_profile_status,
                payload=profile_payload,
            )
        )
    else:
        print("PROFILE_STATUS_UNCHANGED")

    payload["profile_status"] = new_profile_status
    payload["profile"] = profile_payload

    save_state(payload)

    print(
        "BR_FORWARD_ACCUMULATION_V1_OK "
        f"status={new_status} "
        f"profile_status={new_profile_status}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
