#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== MARKET_STATE_PNL_SCORECARD_V1 ===")
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
                    COUNT(*) AS trades,
                    SUM(CASE WHEN o.net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN o.net_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(o.gross_pnl), 0) AS gross_pnl,
                    COALESCE(SUM(o.commission), 0) AS commission,
                    COALESCE(SUM(o.net_pnl), 0) AS net_pnl,
                    AVG(o.net_pnl) AS expectancy,
                    SUM(CASE WHEN o.net_pnl > 0 THEN o.net_pnl ELSE 0 END) AS gross_profit,
                    ABS(SUM(CASE WHEN o.net_pnl < 0 THEN o.net_pnl ELSE 0 END)) AS gross_loss
                FROM research.trade_state_snapshots_v1 tss
                JOIN public.trade_outcomes o
                  ON o.id::text = tss.trade_id
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

    candidates = 0
    for row in rows:
        sig, trades, wins, losses, gross, commission, net, expectancy, gp, gl = row
        pf = None
        if gl and float(gl) > 0:
            pf = float(gp) / float(gl)

        status = "INSUFFICIENT_DATA"
        if trades >= 30 and float(net) > 0 and expectancy and float(expectancy) > 0 and pf and pf > 1.1:
            status = "RESEARCH_CANDIDATE"
            candidates += 1

        print(
            "PNL_ROW "
            f"signature={sig} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"gross_pnl={float(gross):.6f} "
            f"commission={float(commission):.6f} "
            f"net_pnl={float(net):.6f} "
            f"expectancy={float(expectancy or 0):.6f} "
            f"profit_factor={pf if pf is not None else 'None'} "
            f"status={status}"
        )

    print("")
    print(f"rows_total={len(rows)}")
    print(f"research_candidates={candidates}")
    print("micro_live_candidates=0")

    verdict = "MARKET_STATE_PNL_SCORECARD_READY"
    if not rows:
        verdict = "MARKET_STATE_PNL_SCORECARD_NO_LINKED_PNL_ROWS"

    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
