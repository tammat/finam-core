#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== GLOBAL_EDGE_CANDIDATE_AUDIT_V1 ===")
    print("mode=audit_read_only")
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
                SELECT run_id
                FROM research.analytics_global_edge_scorecard_runs_v1
                ORDER BY run_id DESC
                LIMIT 1;
            """)
            row = cur.fetchone()
            if not row:
                print("VERDICT=GLOBAL_EDGE_CANDIDATE_AUDIT_NO_RUN")
                return 1

            run_id = row[0]

            cur.execute("""
                SELECT
                    id,
                    symbol,
                    strategy,
                    timeframe,
                    instrument_signature,
                    fx_signature,
                    energy_signature,
                    trades,
                    wins,
                    losses,
                    winrate,
                    net_pnl,
                    expectancy,
                    profit_factor,
                    first_trade,
                    last_trade,
                    status,
                    reason
                FROM research.analytics_global_edge_scorecard_v1
                WHERE run_id=%s
                  AND status='RESEARCH_CANDIDATE'
                ORDER BY net_pnl DESC, trades DESC;
            """, (run_id,))
            candidates = cur.fetchall()

    print("")
    print("CANDIDATE_ROWS")

    for (
        row_id,
        symbol,
        strategy,
        timeframe,
        instrument_signature,
        fx_signature,
        energy_signature,
        trades,
        wins,
        losses,
        winrate,
        net_pnl,
        expectancy,
        profit_factor,
        first_trade,
        last_trade,
        status,
        reason,
    ) in candidates:
        print(
            "CANDIDATE "
            f"scorecard_row_id={row_id} "
            f"symbol={symbol} "
            f"strategy={strategy or 'UNKNOWN'} "
            f"timeframe={timeframe} "
            f"instrument_signature={instrument_signature} "
            f"fx_signature={fx_signature} "
            f"energy_signature={energy_signature} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={float(winrate or 0):.4f} "
            f"net_pnl={float(net_pnl or 0):.6f} "
            f"expectancy={float(expectancy or 0):.6f} "
            f"profit_factor={float(profit_factor or 0):.6f} "
            f"first_trade={first_trade} "
            f"last_trade={last_trade} "
            f"status={status} "
            f"reason={reason}"
        )

    print("")
    print("SUMMARY")
    print(f"run_id={run_id}")
    print(f"candidate_rows={len(candidates)}")
    print("micro_live_candidates=0")
    print("promotion_allowed=0")

    print("")
    print("NEXT_STEPS")
    print("next=GLOBAL_EDGE_CANDIDATE_REGISTRY_SEED_V1")
    print("next=GLOBAL_EDGE_CANDIDATE_ROBUSTNESS_AUDIT_V1")

    print("")
    print("VERDICT=GLOBAL_EDGE_CANDIDATE_AUDIT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
