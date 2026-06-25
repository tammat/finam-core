#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== HISTORICAL_MARKET_STATE_PNL_SCORECARD_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    tss.entry_compact_signature,
                    MIN(s.canonical_signature) AS canonical_signature,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN ct.net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN ct.net_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(ct.net_pnl), 0) AS net_pnl,
                    AVG(ct.net_pnl) AS expectancy,
                    SUM(CASE WHEN ct.net_pnl > 0 THEN ct.net_pnl ELSE 0 END) AS gross_profit,
                    ABS(SUM(CASE WHEN ct.net_pnl < 0 THEN ct.net_pnl ELSE 0 END)) AS gross_loss,
                    MIN(ct.entry_ts) AS first_trade,
                    MAX(ct.entry_ts) AS last_trade
                FROM research.trade_state_snapshots_v1 tss
                JOIN public.closed_trades ct
                  ON ct.id::text = tss.trade_id
                LEFT JOIN research.market_state_snapshots_v1 s
                  ON s.snapshot_id = tss.entry_snapshot_id
                WHERE tss.link_quality='EXACT_OR_NEAREST_OK'
                  AND tss.entry_compact_signature IS NOT NULL
                GROUP BY tss.entry_compact_signature
                ORDER BY trades DESC, net_pnl DESC;
            """)
            rows = cur.fetchall()

    print("")
    print("HISTORICAL_PNL_ROWS")

    candidates = 0
    positive = 0

    for row in rows:
        sig, canonical, trades, wins, losses, net, expectancy, gp, gl, first_ts, last_ts = row
        pf = None
        if gl and float(gl) > 0:
            pf = float(gp) / float(gl)

        winrate = float(wins) / float(trades) if trades else 0.0

        status = "INSUFFICIENT_DATA"
        if float(net) > 0 and float(expectancy or 0) > 0:
            positive += 1
            status = "POSITIVE_OBSERVATION"
        if trades >= 30 and float(net) > 0 and float(expectancy or 0) > 0 and pf and pf > 1.1:
            candidates += 1
            status = "RESEARCH_CANDIDATE"

        print(
            "PNL_ROW "
            f"signature={sig} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={winrate:.4f} "
            f"net_pnl={float(net):.6f} "
            f"expectancy={float(expectancy or 0):.6f} "
            f"profit_factor={pf if pf is not None else 'None'} "
            f"first_trade={first_ts} "
            f"last_trade={last_ts} "
            f"status={status}"
        )
        print(f"CANONICAL {canonical}")

    print("")
    print(f"rows_total={len(rows)}")
    print(f"positive_rows={positive}")
    print(f"research_candidates={candidates}")
    print("micro_live_candidates=0")

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_INDEX_STATE_CONTEXT_PLAN_V1")
    print("next=HISTORICAL_MARKET_STATE_EDGE_DECISION_V1")

    print("")
    print("VERDICT=HISTORICAL_MARKET_STATE_PNL_SCORECARD_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
