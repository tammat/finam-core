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
    p.add_argument("--min-trades", type=int, default=10)
    p.add_argument("--apply", action="store_true")
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


def metrics(values: list[float]) -> dict:
    trades = len(values)
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net = sum(values)

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "winrate": round(100.0 * len(wins) / trades, 2) if trades else 0,
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else None,
    }


def decision(m: dict, min_trades: int) -> tuple[str, str]:
    pf = m["profit_factor"]

    if m["trades"] < min_trades:
        return "WATCH", "insufficient_sample"

    if m["expectancy"] > 0 and pf is not None and pf >= 1.2:
        return "ALLOW", "positive_expectancy_and_pf"

    if m["expectancy"] <= 0:
        return "BLOCK", "negative_expectancy"

    return "WATCH", "positive_expectancy_but_weak_pf"


def main() -> None:
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    dsn = os.environ["DATABASE_URL"]

    print("=== SESSION SIDE EDGE FILTER CANDIDATE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(symbols)}")
    print(f"trade_source={args.trade_source}")
    print(f"source={args.source}")
    print(f"min_trades={args.min_trades}")
    print(f"apply={int(args.apply)}")
    print()

    sql = """
        SELECT
            symbol,
            side,
            net_pnl,
            COALESCE(entry_ts, opened_at, created_at) AS entry_ts
        FROM closed_trades
        WHERE symbol = ANY(%s)
          AND trade_source = %s
          AND source = %s
          AND net_pnl IS NOT NULL
        ORDER BY symbol, COALESCE(entry_ts, opened_at, created_at), id;
    """

    groups: dict[tuple[str, str, str], list[float]] = {}

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
                key = (
                    row["symbol"],
                    str(row["side"] or "UNKNOWN"),
                    session,
                )
                groups.setdefault(key, []).append(float(row["net_pnl"] or 0))

            print("CANDIDATE_ROWS")

            allow = 0
            block = 0
            watch = 0

            candidate_rows = []

            for key in sorted(groups):
                symbol, side, session = key
                m = metrics(groups[key])
                action, reason = decision(m, args.min_trades)

                if action == "ALLOW":
                    allow += 1
                elif action == "BLOCK":
                    block += 1
                else:
                    watch += 1

                candidate = {
                    "symbol": symbol,
                    "side": side,
                    "session": session,
                    "trades": m["trades"],
                    "wins": m["wins"],
                    "losses": m["losses"],
                    "net_pnl": m["net_pnl"],
                    "expectancy": m["expectancy"],
                    "winrate": m["winrate"],
                    "profit_factor": m["profit_factor"],
                    "action": action,
                    "reason": reason,
                }
                candidate_rows.append(candidate)

                print(
                    "CANDIDATE_ROW "
                    f"symbol={symbol} "
                    f"side={side} "
                    f"session={session} "
                    f"trades={m['trades']} "
                    f"wins={m['wins']} "
                    f"losses={m['losses']} "
                    f"net_pnl={m['net_pnl']} "
                    f"expectancy={m['expectancy']} "
                    f"winrate={m['winrate']} "
                    f"profit_factor={m['profit_factor']} "
                    f"action={action} "
                    f"reason={reason}"
                )

            if args.apply:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS session_side_edge_filter_candidates_v1 (
                        id BIGSERIAL PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        session TEXT NOT NULL,
                        trades INTEGER NOT NULL,
                        wins INTEGER NOT NULL,
                        losses INTEGER NOT NULL,
                        net_pnl DOUBLE PRECISION NOT NULL,
                        expectancy DOUBLE PRECISION NOT NULL,
                        winrate DOUBLE PRECISION NOT NULL,
                        profit_factor DOUBLE PRECISION,
                        action TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        source TEXT NOT NULL,
                        trade_source TEXT NOT NULL
                    );
                """)

                cur.execute("""
                    DELETE FROM session_side_edge_filter_candidates_v1
                    WHERE symbol = ANY(%s)
                      AND source = %s
                      AND trade_source = %s;
                """, (symbols, args.source, args.trade_source))

                for item in candidate_rows:
                    cur.execute("""
                        INSERT INTO session_side_edge_filter_candidates_v1 (
                            symbol, side, session,
                            trades, wins, losses,
                            net_pnl, expectancy, winrate, profit_factor,
                            action, reason, source, trade_source
                        )
                        VALUES (
                            %(symbol)s, %(side)s, %(session)s,
                            %(trades)s, %(wins)s, %(losses)s,
                            %(net_pnl)s, %(expectancy)s, %(winrate)s, %(profit_factor)s,
                            %(action)s, %(reason)s, %(source)s, %(trade_source)s
                        );
                    """, {
                        **item,
                        "source": args.source,
                        "trade_source": args.trade_source,
                    })

                print(f"CANDIDATES_WRITTEN={len(candidate_rows)}")
            else:
                print("CANDIDATES_WRITTEN=0")

    print()
    print(
        "SUMMARY_ROW "
        f"rows={len(groups)} "
        f"allow={allow} "
        f"block={block} "
        f"watch={watch}"
    )
    print("VERDICT=SESSION_SIDE_EDGE_FILTER_CANDIDATE_RECORDED")
    print("SESSION_SIDE_EDGE_FILTER_CANDIDATE_V1_OK")


if __name__ == "__main__":
    main()
