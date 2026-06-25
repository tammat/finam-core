#!/usr/bin/env python3

import os
import psycopg2


SOURCE = "universe_backfill_v1"

PRIORITY_MAP = {
    "BR": "P1",
    "NG": "P1",
    "USDRUBF": "P1",
    "SBER": "P1",
    "LKOH": "P1",
    "PLZL": "P1",
    "GD": "P2",
    "SV": "P2",
    "GAZP": "P2",
    "NVTK": "P2",
    "SBERP": "P2",
    "T": "P2",
    "X5": "P2",
}


def family(symbol: str) -> str:
    return symbol.split("@")[0].rstrip("0123456789")


def priority(symbol: str) -> str:
    base = family(symbol)
    return PRIORITY_MAP.get(base, "P3")


def main() -> int:
    print("=== GLOBAL_LINK_ROOT_CAUSE_AUDIT_V1 ===")
    print("mode=root_cause_read_only")
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
                WITH trades AS (
                    SELECT
                        ct.id::text AS trade_id,
                        ct.symbol,
                        ct.strategy,
                        ct.timeframe,
                        ct.entry_ts
                    FROM public.closed_trades ct
                    WHERE ct.symbol IS NOT NULL
                      AND ct.timeframe IS NOT NULL
                      AND ct.entry_ts IS NOT NULL
                      AND ct.net_pnl IS NOT NULL
                ),
                links AS (
                    SELECT
                        trade_id,
                        link_quality
                    FROM research.trade_state_snapshots_v1
                )
                SELECT
                    t.trade_id,
                    t.symbol,
                    t.strategy,
                    t.timeframe,
                    t.entry_ts,
                    COALESCE(l.link_quality, 'NO_LINK_ROW') AS link_quality
                FROM trades t
                LEFT JOIN links l
                  ON l.trade_id = t.trade_id
                ORDER BY t.symbol, t.timeframe, t.entry_ts;
            """)
            rows = cur.fetchall()

            result_rows = []

            for trade_id, symbol, strategy, timeframe, entry_ts, link_quality in rows:
                if link_quality == "EXACT_OR_NEAREST_OK":
                    root_cause = "LINKED_OK"
                    repair_action = "NONE"
                    repair_priority = "NONE"
                else:
                    cur.execute("""
                        SELECT COUNT(*)
                        FROM public.feature_snapshots
                        WHERE symbol=%s
                          AND timeframe=%s;
                    """, (symbol, timeframe))
                    feature_count = int(cur.fetchone()[0])

                    cur.execute("""
                        SELECT COUNT(*)
                        FROM research.market_state_snapshots_v1
                        WHERE symbol=%s
                          AND timeframe=%s
                          AND source=%s;
                    """, (symbol, timeframe, SOURCE))
                    state_count = int(cur.fetchone()[0])

                    cur.execute("""
                        SELECT COUNT(*)
                        FROM research.market_state_snapshots_v1
                        WHERE symbol=%s
                          AND source=%s;
                    """, (symbol, SOURCE))
                    symbol_state_count = int(cur.fetchone()[0])

                    if feature_count == 0:
                        root_cause = "NO_FEATURE_SNAPSHOT"
                        repair_action = "BACKFILL_FEATURE_SNAPSHOTS"
                    elif state_count == 0 and symbol_state_count > 0:
                        root_cause = "TIMEFRAME_MISMATCH"
                        repair_action = "BACKFILL_OR_MAP_TIMEFRAME"
                    elif state_count == 0:
                        root_cause = "NO_MARKET_STATE"
                        repair_action = "BACKFILL_MARKET_STATE"
                    else:
                        root_cause = "OUTSIDE_HISTORY"
                        repair_action = "EXTEND_HISTORY_WINDOW"

                    repair_priority = priority(symbol)

                result_rows.append(
                    (
                        trade_id,
                        symbol,
                        strategy or "UNKNOWN",
                        timeframe,
                        entry_ts,
                        link_quality,
                        root_cause,
                        repair_action,
                        repair_priority,
                    )
                )

    total = len(result_rows)
    linked = sum(1 for r in result_rows if r[5] == "EXACT_OR_NEAREST_OK")
    lost = total - linked
    coverage = linked / total if total else 0.0

    print("")
    print("EXECUTIVE_SUMMARY")
    print(f"closed_trades={total}")
    print(f"linked={linked}")
    print(f"lost={lost}")
    print(f"coverage={coverage:.4f}")

    print("")
    print("ROOT_CAUSE_ROWS")
    for row in result_rows:
        trade_id, symbol, strategy, timeframe, entry_ts, link_quality, root_cause, repair_action, repair_priority = row
        if root_cause == "LINKED_OK":
            continue
        print(
            "ROOT_CAUSE_ROW "
            f"trade_id={trade_id} "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"entry_ts={entry_ts} "
            f"link_quality={link_quality} "
            f"root_cause={root_cause} "
            f"repair_action={repair_action} "
            f"repair_priority={repair_priority}"
        )

    print("")
    print("ROOT_CAUSE_SUMMARY")
    summary = {}
    for row in result_rows:
        root_cause = row[6]
        if root_cause == "LINKED_OK":
            continue
        summary[root_cause] = summary.get(root_cause, 0) + 1
    for cause, count in sorted(summary.items()):
        print(f"CAUSE name={cause} count={count}")

    print("")
    print("INSTRUMENT_SUMMARY")
    instrument_summary = {}
    for row in result_rows:
        symbol = row[1]
        if symbol not in instrument_summary:
            instrument_summary[symbol] = {"total": 0, "linked": 0}
        instrument_summary[symbol]["total"] += 1
        if row[5] == "EXACT_OR_NEAREST_OK":
            instrument_summary[symbol]["linked"] += 1

    for symbol, stats in sorted(instrument_summary.items()):
        pct = stats["linked"] / stats["total"] if stats["total"] else 0.0
        print(
            "INSTRUMENT "
            f"symbol={symbol} "
            f"priority={priority(symbol)} "
            f"trades={stats['total']} "
            f"linked={stats['linked']} "
            f"coverage={pct:.4f}"
        )

    if coverage >= 0.90:
        verdict = "GLOBAL_LINK_ROOT_CAUSE_AUDIT_READY_FOR_CONTEXT_LINKING"
    elif coverage >= 0.70:
        verdict = "GLOBAL_LINK_ROOT_CAUSE_AUDIT_WARNING_REPAIR_RECOMMENDED"
    else:
        verdict = "GLOBAL_LINK_ROOT_CAUSE_AUDIT_REPAIR_REQUIRED"

    print("")
    print("NEXT_STEPS")
    print("next=GLOBAL_LINK_REPAIR_PLAN_V1")

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
