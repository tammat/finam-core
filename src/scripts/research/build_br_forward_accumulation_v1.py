from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


STATE_FILE = Path("runtime_state/br_forward_accumulation_state.json")

SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"


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
        "📊 BR FORWARD ACCUMULATION UPDATE\n"
        f"Статус: {old_status} → {new_status}\n"
        f"PF: {payload['pf']:.6f}\n"
        f"Expectancy: {payload['expectancy']:.6f}\n"
        f"Trades: {payload['trades']}\n"
        f"Repeatability: {str(payload['repeatability_confirmed']).lower()}\n"
        f"Contamination: {payload['contamination']}\n"
    )


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("TELEGRAM_DISABLED")
        return

    import requests

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
        },
        timeout=15,
    )

    print(
        f"TELEGRAM_NOTIFY status_code={response.status_code}",
        flush=True,
    )


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

    save_state(payload)

    print(
        "BR_FORWARD_ACCUMULATION_V1_OK "
        f"status={new_status}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
