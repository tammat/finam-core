from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_VALIDATION_PIPELINE_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict) -> dict:
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))

    sample_check_status = "PASS" if trades >= 30 else "WAIT_SAMPLE"

    if pf >= Decimal("1.2"):
        pf_check_status = "PASS"
    elif pf >= Decimal("1.0"):
        pf_check_status = "WATCH"
    else:
        pf_check_status = "FAIL"

    if expectancy > Decimal("0"):
        expectancy_check_status = "PASS"
    elif expectancy == Decimal("0"):
        expectancy_check_status = "WATCH"
    else:
        expectancy_check_status = "FAIL"

    if trades < 30:
        pipeline_status = "ACCUMULATE_SAMPLE"
        recommended_action = "Накопить выборку Paper Runtime до 30+ сделок."
        robustness_status = "WAITING"
        oos_status = "WAITING"
    elif pf >= Decimal("1.2") and expectancy > Decimal("0"):
        pipeline_status = "READY_FOR_ROBUSTNESS"
        recommended_action = "Запустить robustness-проверку кандидата."
        robustness_status = "REQUIRED"
        oos_status = "WAITING"
    elif pf >= Decimal("1.0") and expectancy >= Decimal("0"):
        pipeline_status = "OBSERVE_MORE"
        recommended_action = "Продолжить наблюдение и проверить устойчивость по времени."
        robustness_status = "WAITING"
        oos_status = "WAITING"
    else:
        pipeline_status = "REJECTED_BY_RULES"
        recommended_action = "Не продвигать кандидата без дополнительного анализа."
        robustness_status = "NOT_ALLOWED"
        oos_status = "NOT_ALLOWED"

    return {
        "sample_check_status": sample_check_status,
        "pf_check_status": pf_check_status,
        "expectancy_check_status": expectancy_check_status,
        "robustness_status": robustness_status,
        "oos_status": oos_status,
        "pipeline_status": pipeline_status,
        "recommended_action": recommended_action,
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_VALIDATION_PIPELINE_V1 ===")

            cur.execute("""
                SELECT
                    queue_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    validation_status,
                    priority,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    evidence_summary,
                    risk_notes
                FROM marketcore_ui.edge_validation_queue_v1
                ORDER BY
                    CASE
                        WHEN validation_status='READY_FOR_EDGE_VALIDATION' THEN 1
                        WHEN validation_status='WATCHLIST' THEN 2
                        WHEN validation_status='ACCUMULATE_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    queue_rank;
            """)
            queue_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_validation_pipeline_v1;")

            for idx, row in enumerate(queue_rows, start=1):
                c = classify(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_validation_pipeline_v1 (
                        pipeline_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        queue_status,
                        priority,
                        sample_check_status,
                        pf_check_status,
                        expectancy_check_status,
                        robustness_status,
                        oos_status,
                        pipeline_status,
                        recommended_action,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        source_queue_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("validation_status") or "UNKNOWN",
                    row.get("priority") or "NORMAL",
                    c["sample_check_status"],
                    c["pf_check_status"],
                    c["expectancy_check_status"],
                    c["robustness_status"],
                    c["oos_status"],
                    c["pipeline_status"],
                    c["recommended_action"],
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    row.get("evidence_summary") or "",
                    row.get("risk_notes") or "",
                    row.get("queue_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_validation_pipeline_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT pipeline_status, count(*) AS rows
                FROM marketcore_ui.edge_validation_pipeline_v1
                GROUP BY pipeline_status
                ORDER BY pipeline_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"pipeline_status_{row['pipeline_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY")


if __name__ == "__main__":
    main()
