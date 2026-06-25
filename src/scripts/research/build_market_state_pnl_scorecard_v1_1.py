#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== MARKET_STATE_PNL_SCORECARD_V1_1 ===")
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
                    SUM(CASE WHEN o.net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN o.net_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(o.gross_pnl), 0) AS gross_pnl,
                    COALESCE(SUM(o.commission), 0) AS commission,
                    COALESCE(SUM(o.net_pnl), 0) AS net_pnl,
                    AVG(o.net_pnl) AS expectancy,
                    SUM(CASE WHEN o.net_pnl > 0 THEN o.net_pnl ELSE 0 END) AS gross_profit,
                    ABS(SUM(CASE WHEN o.net_pnl < 0 THEN o.net_pnl ELSE 0 END)) AS gross_loss,
                    MIN(o.entry_ts) AS first_trade,
                    MAX(o.entry_ts) AS last_trade
                FROM research.trade_state_snapshots_v1 tss
                JOIN public.trade_outcomes o
                  ON o.id::text = tss.trade_id
                LEFT JOIN research.market_state_snapshots_v1 s
                  ON s.snapshot_id = tss.entry_snapshot_id
                WHERE tss.link_quality='EXACT_OR_NEAREST_OK'
                  AND tss.entry_compact_signature IS NOT NULL
                GROUP BY tss.entry_compact_signature
                ORDER BY trades DESC, net_pnl DESC;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT
                    COUNT(*),
                    SUM(CASE WHEN link_quality='EXACT_OR_NEAREST_OK' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN link_quality='NO_SNAPSHOT' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN link_quality='ENTRY_ONLY' THEN 1 ELSE 0 END)
                FROM research.trade_state_snapshots_v1;
            """)
            total, ok, no_snapshot, entry_only = cur.fetchone()

    print("")
    print("LINK_SUMMARY")
    print(f"linked_total={total}")
    print(f"link_ok={ok}")
    print(f"no_snapshot={no_snapshot}")
    print(f"entry_only={entry_only}")

    print("")
    print("PNL_SCORECARD_ROWS")

    research_candidates = 0
    positive_rows = 0

    for row in rows:
        (
            sig,
            canonical,
            trades,
            wins,
            losses,
            gross,
            commission,
            net,
            expectancy,
            gross_profit,
            gross_loss,
            first_trade,
            last_trade,
        ) = row

        pf = None
        if gross_loss and float(gross_loss) > 0:
            pf = float(gross_profit) / float(gross_loss)

        winrate = float(wins) / float(trades) if trades else 0.0

        status = "INSUFFICIENT_DATA"
        if float(net) > 0 and float(expectancy or 0) > 0:
            positive_rows += 1
            status = "POSITIVE_BUT_INSUFFICIENT_SAMPLE"

        if trades >= 30 and float(net) > 0 and float(expectancy or 0) > 0 and pf and pf > 1.1:
            status = "RESEARCH_CANDIDATE"
            research_candidates += 1

        print(
            "PNL_ROW "
            f"signature={sig} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={winrate:.4f} "
            f"gross_pnl={float(gross):.6f} "
            f"commission={float(commission):.6f} "
            f"net_pnl={float(net):.6f} "
            f"expectancy={float(expectancy or 0):.6f} "
            f"profit_factor={pf if pf is not None else 'None'} "
            f"first_trade={first_trade} "
            f"last_trade={last_trade} "
            f"status={status}"
        )
        print(f"CANONICAL {canonical}")

    print("")
    print(f"rows_total={len(rows)}")
    print(f"positive_rows={positive_rows}")
    print(f"research_candidates={research_candidates}")
    print("micro_live_candidates=0")

    verdict = "MARKET_STATE_PNL_SCORECARD_V1_1_READY"
    if not rows:
        verdict = "MARKET_STATE_PNL_SCORECARD_V1_1_NO_LINKED_PNL_ROWS"

    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
