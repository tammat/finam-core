from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_OOS_VALIDATION_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict) -> dict:
    robustness_status = str(row.get("robustness_status") or "UNKNOWN")
    robustness_score = dec(row.get("robustness_score"))
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))

    if robustness_status == "WAIT_SAMPLE":
        return {
            "oos_status": "WAIT_SAMPLE",
            "oos_readiness": "NOT_READY",
            "micro_live_ready": False,
            "oos_reason": "Недостаточная выборка. OOS-проверка преждевременна.",
            "recommended_action": "Накопить выборку Paper Runtime.",
        }

    if robustness_status == "ROBUSTNESS_REQUIRED":
        if robustness_score >= Decimal("0.75") and trades >= 30 and pf >= Decimal("1.2") and expectancy > Decimal("0"):
            return {
                "oos_status": "READY_FOR_OOS",
                "oos_readiness": "READY",
                "micro_live_ready": False,
                "oos_reason": "Кандидат прошёл первичные robustness-фильтры и готов к out-of-sample проверке.",
                "recommended_action": "Запустить EDGE_OOS_BACKTEST_V1.",
            }

        return {
            "oos_status": "ROBUSTNESS_WEAK",
            "oos_readiness": "NOT_READY",
            "micro_live_ready": False,
            "oos_reason": "Robustness-score недостаточен для OOS.",
            "recommended_action": "Продолжить robustness-анализ.",
        }

    if robustness_status == "WATCHLIST":
        return {
            "oos_status": "OBSERVE_MORE",
            "oos_readiness": "WATCH",
            "micro_live_ready": False,
            "oos_reason": "Кандидат требует дополнительного наблюдения до OOS.",
            "recommended_action": "Продолжить наблюдение и накопление данных.",
        }

    return {
        "oos_status": "BLOCKED_BY_ROBUSTNESS",
        "oos_readiness": "BLOCKED",
        "micro_live_ready": False,
        "oos_reason": "Кандидат не прошёл robustness-фильтры.",
        "recommended_action": "Не продвигать в OOS.",
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_OOS_VALIDATION_V1 ===")

            cur.execute("""
                SELECT
                    robustness_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    robustness_status,
                    sample_size_status,
                    pf_status,
                    expectancy_status,
                    winrate_status,
                    pnl_status,
                    robustness_score,
                    oos_required,
                    micro_live_ready,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    evidence_summary,
                    weakness_summary,
                    recommended_action
                FROM marketcore_ui.edge_robustness_check_v1
                ORDER BY
                    CASE
                        WHEN robustness_status='ROBUSTNESS_REQUIRED' THEN 1
                        WHEN robustness_status='WATCHLIST' THEN 2
                        WHEN robustness_status='WAIT_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    robustness_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_oos_validation_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_oos_validation_v1 (
                        oos_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        robustness_status,
                        oos_status,
                        oos_readiness,
                        sample_size_status,
                        pf_status,
                        expectancy_status,
                        winrate_status,
                        pnl_status,
                        robustness_score,
                        oos_required,
                        micro_live_ready,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        oos_reason,
                        recommended_action,
                        source_robustness_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("robustness_status") or "UNKNOWN",
                    c["oos_status"],
                    c["oos_readiness"],
                    row.get("sample_size_status") or "UNKNOWN",
                    row.get("pf_status") or "UNKNOWN",
                    row.get("expectancy_status") or "UNKNOWN",
                    row.get("winrate_status") or "UNKNOWN",
                    row.get("pnl_status") or "UNKNOWN",
                    row.get("robustness_score") or 0,
                    row.get("oos_required") or False,
                    c["micro_live_ready"],
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    row.get("evidence_summary") or "",
                    c["oos_reason"],
                    c["recommended_action"],
                    row.get("robustness_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_oos_validation_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT oos_status, count(*) AS rows
                FROM marketcore_ui.edge_oos_validation_v1
                GROUP BY oos_status
                ORDER BY oos_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"oos_status_{row['oos_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_OOS_VALIDATION_V1_READY")


if __name__ == "__main__":
    main()
