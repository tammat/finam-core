#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

MSK = timezone(timedelta(hours=3))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default="BRM6@RTSX,BRN6@RTSX,NGN6@RTSX")
    p.add_argument("--trade-source", default="paper")
    p.add_argument("--source", default="closed_trade_engine_v1_1")
    return p.parse_args()


def session_name(hour: int) -> str:
    if 7 <= hour < 10:
        return "утро_раннее"
    if 10 <= hour < 14:
        return "московская_середина"
    if 14 <= hour < 19:
        return "дневная_вечерняя"
    if 19 <= hour <= 23:
        return "вечерняя_сессия"
    return "ночная_сессия"


def regime_from_payload(payload: dict | None) -> str:
    if not payload:
        return "unknown"

    candidates = [
        payload.get("regime"),
        payload.get("market_regime"),
        payload.get("runtime_regime"),
        payload.get("regime_state"),
        (payload.get("features") or {}).get("regime"),
        (payload.get("features") or {}).get("market_regime"),
        (payload.get("trade_context_snapshot") or {}).get("regime"),
        (payload.get("trade_context_snapshot") or {}).get("market_regime"),
    ]

    for value in candidates:
        if value:
            return str(value)

    return "unknown"


def metrics(values: list[float]) -> dict:
    trades = len(values)
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    net = sum(values)

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "winrate": round(100.0 * len(wins) / trades, 2) if trades else 0,
        "profit_factor": round(gp / gl, 4) if gl > 0 else None,
    }


def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 10:
        return "NO_DATA"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.2:
        return "FAVORABLE"
    if m["expectancy"] > 0:
        return "WATCH"
    return "UNFAVORABLE"


def main() -> None:
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    dsn = os.environ["DATABASE_URL"]

    print("=== SESSION REGIME EDGE MATRIX V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(symbols)}")
    print(f"trade_source={args.trade_source}")
    print(f"source={args.source}")
    print()

    sql = """
        SELECT
            symbol,
            strategy,
            timeframe,
            side,
            net_pnl,
            COALESCE(entry_ts, opened_at, created_at) AS entry_ts,
            payload
        FROM closed_trades
        WHERE symbol = ANY(%s)
          AND trade_source = %s
          AND source = %s
          AND net_pnl IS NOT NULL
        ORDER BY symbol, COALESCE(entry_ts, opened_at, created_at), id;
    """

    matrix: dict[tuple[str, str, str, str], list[float]] = {}

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (symbols, args.trade_source, args.source))
            rows = cur.fetchall()

    for row in rows:
        ts = row["entry_ts"]
        if ts is None:
            continue

        hour = ts.astimezone(MSK).hour
        session = session_name(hour)
        regime = regime_from_payload(row.get("payload"))

        key = (
            row["symbol"],
            str(row["side"] or "UNKNOWN"),
            session,
            regime,
        )
        matrix.setdefault(key, []).append(float(row["net_pnl"] or 0))

    print("SESSION_REGIME_ROWS")

    favorable = 0
    unfavorable = 0
    watch = 0
    no_data = 0

    for key in sorted(matrix):
        symbol, side, session, regime = key
        m = metrics(matrix[key])
        st = status(m)

        if st == "FAVORABLE":
            favorable += 1
        elif st == "UNFAVORABLE":
            unfavorable += 1
        elif st == "WATCH":
            watch += 1
        else:
            no_data += 1

        print(
            "SESSION_REGIME_ROW "
            f"symbol={symbol} "
            f"side={side} "
            f"session={session} "
            f"regime={regime} "
            f"trades={m['trades']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"status={st}"
        )

    print()
    print(
        "SUMMARY_ROW "
        f"rows={len(matrix)} "
        f"favorable={favorable} "
        f"watch={watch} "
        f"unfavorable={unfavorable} "
        f"no_data={no_data}"
    )
    print("VERDICT=SESSION_REGIME_EDGE_MATRIX_RECORDED")
    print("SESSION_REGIME_EDGE_MATRIX_V1_OK")


if __name__ == "__main__":
    main()
