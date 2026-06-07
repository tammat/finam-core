#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict

import psycopg2
import psycopg2.extras


BR_TRUSTED_FROM = "2026-06-05 00:00:00+00"
NG_TRUSTED_FROM = "2026-06-03 00:00:00+00"
SOURCE = "closed_trade_engine_v1_1"


def profit_factor(gross_profit: float, gross_loss: float) -> str:
    if gross_loss == 0:
        return "None"
    return f"{gross_profit / abs(gross_loss):.6f}"


def main() -> None:
    print("=== EXIT REASON PROFIT FACTOR REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=trusted_window_only")
    print(f"source={SOURCE}")
    print(f"br_trusted_from={BR_TRUSTED_FROM}")
    print(f"ng_trusted_from={NG_TRUSTED_FROM}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    stats = defaultdict(lambda: {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "net_pnl": 0.0,
    })

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    CASE
                        WHEN symbol LIKE 'BR%%' THEN 'BR'
                        WHEN symbol LIKE 'NG%%' THEN 'NG'
                        ELSE 'OTHER'
                    END AS root,
                    symbol,
                    COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason,
                    COALESCE(net_pnl, 0)::float AS net_pnl
                FROM closed_trades
                WHERE source = %s
                  AND (
                        (
                            symbol LIKE 'BR%%'
                            AND COALESCE(exit_ts, closed_at, created_at) >= %s
                        )
                     OR (
                            symbol LIKE 'NG%%'
                            AND COALESCE(exit_ts, closed_at, created_at) >= %s
                        )
                  )
                ORDER BY root, exit_reason, symbol
                """,
                (SOURCE, BR_TRUSTED_FROM, NG_TRUSTED_FROM),
            )
            rows = cur.fetchall()

    for r in rows:
        root = str(r["root"])
        reason = str(r["exit_reason"] or "NO_MATCH")
        pnl = float(r["net_pnl"] or 0.0)
        key = (root, reason)

        s = stats[key]
        s["trades"] += 1
        s["net_pnl"] += pnl

        if pnl > 0:
            s["wins"] += 1
            s["gross_profit"] += pnl
        elif pnl < 0:
            s["losses"] += 1
            s["gross_loss"] += pnl

    print("EXIT_REASON_RESULTS")
    for (root, reason), s in sorted(stats.items()):
        trades = int(s["trades"])
        wins = int(s["wins"])
        losses = int(s["losses"])
        net_pnl = float(s["net_pnl"])
        winrate = wins / trades if trades else 0.0
        expectancy = net_pnl / trades if trades else 0.0
        pf = profit_factor(float(s["gross_profit"]), float(s["gross_loss"]))

        print(
            f"REASON_ROW root={root} reason={reason} "
            f"trades={trades} wins={wins} losses={losses} "
            f"winrate={winrate:.4f} "
            f"gross_profit={float(s['gross_profit']):.6f} "
            f"gross_loss={float(s['gross_loss']):.6f} "
            f"net_pnl={net_pnl:.6f} "
            f"expectancy={expectancy:.6f} "
            f"profit_factor={pf}"
        )

    print()
    print("SUMMARY")
    print(f"TRUSTED_ROWS={len(rows)}")
    print("VERDICT=EXIT_REASON_PROFIT_FACTOR_RECORDED")
    print("EXIT_REASON_PROFIT_FACTOR_REPORT_V1_OK")


if __name__ == "__main__":
    main()
