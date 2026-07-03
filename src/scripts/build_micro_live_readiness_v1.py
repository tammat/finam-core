from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MICRO_LIVE_READINESS_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def classify(row: dict) -> dict:
    backtest_status = str(row.get("backtest_status") or "UNKNOWN")
    oos_status = str(row.get("oos_status") or "UNKNOWN")
    robustness_status = str(row.get("robustness_status") or "UNKNOWN")

    total_trades = int(row.get("total_trades") or 0)
    oos_trades = int(row.get("oos_trades") or 0)
    oos_pf = dec(row.get("oos_profit_factor"))
    oos_exp = dec(row.get("oos_expectancy"))
    stability = dec(row.get("stability_score"))

    if total_trades < 30:
        return {
            "readiness_status": "WAIT_SAMPLE",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Недостаточная общая выборка. Требуется минимум 30 paper-сделок.",
            "recommended_action": "Продолжить Paper Runtime и накопить выборку.",
        }

    if oos_trades < 10:
        return {
            "readiness_status": "WAIT_OOS_SAMPLE",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Недостаточная OOS-выборка. Требуется минимум 10 OOS-сделок.",
            "recommended_action": "Продолжить OOS-наблюдение.",
        }

    if robustness_status not in {"ROBUSTNESS_REQUIRED", "WATCHLIST"}:
        return {
            "readiness_status": "BLOCKED_ROBUSTNESS",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Robustness-фильтр не допускает кандидата к Micro Live.",
            "recommended_action": "Вернуть кандидата на этап robustness или отклонить.",
        }

    if oos_status != "READY_FOR_OOS":
        return {
            "readiness_status": "BLOCKED_OOS",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Кандидат не получил статус READY_FOR_OOS.",
            "recommended_action": "Завершить OOS validation.",
        }

    if backtest_status != "OOS_PASS":
        return {
            "readiness_status": "BLOCKED_BACKTEST",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "OOS backtest не подтвердил устойчивость edge.",
            "recommended_action": "Не переводить в Micro Live.",
        }

    if oos_exp <= Decimal("0") or oos_pf < Decimal("1.0") or stability < Decimal("0.70"):
        return {
            "readiness_status": "BLOCKED_METRICS",
            "micro_live_ready": False,
            "micro_live_allowed": False,
            "block_reason": "Метрики OOS недостаточны для Micro Live.",
            "recommended_action": "Продолжить исследование или отклонить кандидата.",
        }

    return {
        "readiness_status": "READY_FOR_RISK_REVIEW",
        "micro_live_ready": True,
        "micro_live_allowed": False,
        "block_reason": "Торговое преимущество прошло статистические фильтры, но требуется финальная risk approval.",
        "recommended_action": "Передать в MICRO_LIVE_RISK_APPROVAL_V1. Автоматическое включение запрещено.",
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MICRO_LIVE_READINESS_V1 ===")

            cur.execute("""
                SELECT
                    backtest_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    robustness_status,
                    oos_status,
                    oos_readiness,
                    backtest_status,
                    total_trades,
                    in_sample_trades,
                    oos_trades,
                    in_sample_pnl,
                    oos_pnl,
                    in_sample_expectancy,
                    oos_expectancy,
                    in_sample_profit_factor,
                    oos_profit_factor,
                    in_sample_winrate,
                    oos_winrate,
                    stability_score,
                    micro_live_candidate,
                    pass_reason,
                    fail_reason,
                    recommended_action
                FROM marketcore_ui.edge_oos_backtest_v1
                ORDER BY
                    CASE
                        WHEN backtest_status='OOS_PASS' THEN 1
                        WHEN backtest_status='WAIT_OOS_SAMPLE' THEN 2
                        WHEN backtest_status='WAIT_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    backtest_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.micro_live_readiness_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row)

                evidence_summary = (
                    f"Backtest={row.get('backtest_status') or 'UNKNOWN'}; "
                    f"OOS={row.get('oos_status') or 'UNKNOWN'}; "
                    f"Robustness={row.get('robustness_status') or 'UNKNOWN'}; "
                    f"TotalTrades={row.get('total_trades') or 0}; "
                    f"OOSTrades={row.get('oos_trades') or 0}; "
                    f"OOSPF={row.get('oos_profit_factor') or 0}; "
                    f"OOSExpectancy={row.get('oos_expectancy') or 0}; "
                    f"Stability={row.get('stability_score') or 0}"
                )

                cur.execute("""
                    INSERT INTO marketcore_ui.micro_live_readiness_v1 (
                        readiness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        backtest_status,
                        oos_status,
                        robustness_status,
                        readiness_status,
                        micro_live_ready,
                        micro_live_allowed,
                        total_trades,
                        in_sample_trades,
                        oos_trades,
                        in_sample_pnl,
                        oos_pnl,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        in_sample_winrate,
                        oos_winrate,
                        stability_score,
                        block_reason,
                        evidence_summary,
                        recommended_action,
                        source_backtest_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("backtest_status") or "UNKNOWN",
                    row.get("oos_status") or "UNKNOWN",
                    row.get("robustness_status") or "UNKNOWN",
                    c["readiness_status"],
                    c["micro_live_ready"],
                    c["micro_live_allowed"],
                    row.get("total_trades") or 0,
                    row.get("in_sample_trades") or 0,
                    row.get("oos_trades") or 0,
                    row.get("in_sample_pnl"),
                    row.get("oos_pnl"),
                    row.get("in_sample_expectancy"),
                    row.get("oos_expectancy"),
                    row.get("in_sample_profit_factor"),
                    row.get("oos_profit_factor"),
                    row.get("in_sample_winrate"),
                    row.get("oos_winrate"),
                    row.get("stability_score") or 0,
                    c["block_reason"],
                    evidence_summary,
                    c["recommended_action"],
                    row.get("backtest_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.micro_live_readiness_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT readiness_status, count(*) AS rows
                FROM marketcore_ui.micro_live_readiness_v1
                GROUP BY readiness_status
                ORDER BY readiness_status;
            """)
            status_rows = cur.fetchall()

            cur.execute("""
                SELECT count(*) AS ready
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_ready=true;
            """)
            ready_rows = int(cur.fetchone()["ready"])

            cur.execute("""
                SELECT count(*) AS allowed
                FROM marketcore_ui.micro_live_readiness_v1
                WHERE micro_live_allowed=true;
            """)
            allowed_rows = int(cur.fetchone()["allowed"])

    print(f"rows_written={rows_written}")
    print(f"micro_live_ready_rows={ready_rows}")
    print(f"micro_live_allowed_rows={allowed_rows}")
    for row in status_rows:
        print(f"readiness_status_{row['readiness_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MICRO_LIVE_READINESS_V1_READY")


if __name__ == "__main__":
    main()
