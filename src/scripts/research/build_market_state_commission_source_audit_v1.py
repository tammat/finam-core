#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== MARKET_STATE_COMMISSION_SOURCE_AUDIT_V1 ===")
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
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='trade_outcomes'
                ORDER BY ordinal_position;
            """)
            cols = [r[0] for r in cur.fetchall()]

            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN commission IS NULL THEN 1 ELSE 0 END) AS commission_null,
                    SUM(CASE WHEN commission = 0 THEN 1 ELSE 0 END) AS commission_zero,
                    SUM(CASE WHEN commission <> 0 THEN 1 ELSE 0 END) AS commission_nonzero,
                    COALESCE(SUM(commission), 0) AS commission_sum
                FROM public.trade_outcomes;
            """)
            total, nulls, zeros, nonzero, commission_sum = cur.fetchone()

            cur.execute("""
                SELECT
                    COUNT(*),
                    COALESCE(SUM(gross_pnl), 0),
                    COALESCE(SUM(commission), 0),
                    COALESCE(SUM(net_pnl), 0)
                FROM public.trade_outcomes o
                JOIN research.trade_state_snapshots_v1 tss
                  ON tss.trade_id = o.id::text
                WHERE tss.link_quality='EXACT_OR_NEAREST_OK';
            """)
            linked, gross, linked_commission, net = cur.fetchone()

    print("")
    print("TRADE_OUTCOMES_COLUMNS")
    print("columns=" + ",".join(cols))

    print("")
    print("COMMISSION_SUMMARY")
    print(f"trade_outcomes_total={total}")
    print(f"commission_null={nulls}")
    print(f"commission_zero={zeros}")
    print(f"commission_nonzero={nonzero}")
    print(f"commission_sum={float(commission_sum):.6f}")

    print("")
    print("LINKED_PNL_COMMISSION")
    print(f"linked_trades={linked}")
    print(f"linked_gross_pnl={float(gross):.6f}")
    print(f"linked_commission={float(linked_commission):.6f}")
    print(f"linked_net_pnl={float(net):.6f}")

    verdict = "MARKET_STATE_COMMISSION_SOURCE_AUDIT_OK"
    if total and nonzero == 0:
        verdict = "MARKET_STATE_COMMISSION_SOURCE_AUDIT_COMMISSION_ZERO_SOURCE_WEAK"

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_STATE_COMMISSION_REPAIR_PLAN_V1")
    print("next=MARKET_STATE_SAMPLE_EXPANSION_PLAN_V1")

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
