from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_SAMPLE_ACCUMULATION_MONITOR_V1"
REQUIRED_TOTAL_TRADES = 30
REQUIRED_OOS_TRADES = 10


def progress(total_trades: int, oos_trades: int) -> Decimal:
    total_part = min(total_trades, REQUIRED_TOTAL_TRADES) / REQUIRED_TOTAL_TRADES
    oos_part = min(oos_trades, REQUIRED_OOS_TRADES) / REQUIRED_OOS_TRADES
    return Decimal(str(round((total_part * 0.70 + oos_part * 0.30) * 100, 2)))


def classify(total_trades: int, oos_trades: int) -> tuple[str, str]:
    remaining_total = max(REQUIRED_TOTAL_TRADES - total_trades, 0)
    remaining_oos = max(REQUIRED_OOS_TRADES - oos_trades, 0)

    if remaining_total == 0 and remaining_oos == 0:
        return "SAMPLE_READY", "Выборка достаточна. Можно продолжать Micro Live readiness / risk review."

    if remaining_total > 0 and remaining_oos > 0:
        return "WAIT_BOTH_SAMPLE", "Продолжить Paper Runtime: не хватает общей и OOS-выборки."

    if remaining_total > 0:
        return "WAIT_TOTAL_SAMPLE", "Продолжить Paper Runtime: не хватает общей выборки."

    return "WAIT_OOS_SAMPLE", "Продолжить OOS-наблюдение: не хватает OOS-сделок."


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_SAMPLE_ACCUMULATION_MONITOR_V1 ===")

            cur.execute("""
                SELECT
                    readiness_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    readiness_status,
                    backtest_status,
                    oos_status,
                    robustness_status,
                    total_trades,
                    oos_trades,
                    micro_live_ready,
                    micro_live_allowed,
                    block_reason,
                    recommended_action
                FROM marketcore_ui.micro_live_readiness_v1
                ORDER BY
                    CASE
                        WHEN readiness_status IN ('WAIT_SAMPLE','WAIT_OOS_SAMPLE') THEN 1
                        WHEN readiness_status LIKE 'BLOCKED%' THEN 2
                        WHEN readiness_status='READY_FOR_RISK_REVIEW' THEN 3
                        ELSE 4
                    END,
                    readiness_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")

            for idx, row in enumerate(rows, start=1):
                total_trades = int(row.get("total_trades") or 0)
                oos_trades = int(row.get("oos_trades") or 0)

                remaining_total = max(REQUIRED_TOTAL_TRADES - total_trades, 0)
                remaining_oos = max(REQUIRED_OOS_TRADES - oos_trades, 0)

                sample_status, sample_action = classify(total_trades, oos_trades)

                recommended_action = sample_action
                if row.get("recommended_action"):
                    recommended_action = f"{sample_action} Previous gate: {row.get('recommended_action')}"

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_sample_accumulation_monitor_v1 (
                        monitor_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        readiness_status,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        total_trades,
                        required_total_trades,
                        remaining_total_trades,
                        oos_trades,
                        required_oos_trades,
                        remaining_oos_trades,
                        sample_status,
                        progress_pct,
                        micro_live_ready,
                        micro_live_allowed,
                        block_reason,
                        recommended_action,
                        source_readiness_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("readiness_status") or "UNKNOWN",
                    row.get("backtest_status") or "UNKNOWN",
                    row.get("oos_status") or "UNKNOWN",
                    row.get("robustness_status") or "UNKNOWN",
                    total_trades,
                    REQUIRED_TOTAL_TRADES,
                    remaining_total,
                    oos_trades,
                    REQUIRED_OOS_TRADES,
                    remaining_oos,
                    sample_status,
                    progress(total_trades, oos_trades),
                    bool(row.get("micro_live_ready") or False),
                    bool(row.get("micro_live_allowed") or False),
                    row.get("block_reason") or "",
                    recommended_action,
                    row.get("readiness_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT sample_status, count(*) AS rows
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                GROUP BY sample_status
                ORDER BY sample_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"sample_status_{row['sample_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY")


if __name__ == "__main__":
    main()
