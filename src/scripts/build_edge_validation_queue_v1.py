from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_VALIDATION_QUEUE_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def status_for(row: dict) -> tuple[str, str, str, str]:
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))

    if trades < 30:
        return (
            "ACCUMULATE_SAMPLE",
            "LOW",
            "Накопить выборку Paper Runtime",
            "Выборка меньше 30 сделок; статистическая устойчивость не подтверждена.",
        )

    if pf >= Decimal("1.2") and expectancy > Decimal("0"):
        return (
            "READY_FOR_EDGE_VALIDATION",
            "HIGH",
            "Передать в Edge Validation",
            "PF выше минимального порога и expectancy положительное; требуется устойчивость и OOS.",
        )

    if pf >= Decimal("1.0") and expectancy >= Decimal("0"):
        return (
            "WATCHLIST",
            "NORMAL",
            "Наблюдать и проверить устойчивость",
            "Результат не отрицательный, но запас преимущества недостаточен для немедленного продвижения.",
        )

    return (
        "REJECT_REVIEW",
        "LOW",
        "Не продвигать без дополнительного анализа",
        "Текущая статистика не подтверждает edge.",
    )


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_VALIDATION_QUEUE_V1 ===")

            cur.execute("""
                SELECT
                    queue_rank,
                    symbol,
                    recommended_strategy_family AS strategy,
                    timeframe,
                    ''::text AS side,
                    candidate_status,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    source_table,
                    refreshed_at
                FROM marketcore_ui.market_universe_research_queue_v1
                ORDER BY
                    CASE
                        WHEN COALESCE(trades,0) >= 30
                         AND COALESCE(profit_factor,0) >= 1.2
                         AND COALESCE(expectancy,0) > 0 THEN 1
                        WHEN COALESCE(trades,0) >= 30
                         AND COALESCE(profit_factor,0) >= 1.0
                         AND COALESCE(expectancy,0) >= 0 THEN 2
                        WHEN COALESCE(trades,0) < 30 THEN 3
                        ELSE 4
                    END,
                    COALESCE(score,0) DESC,
                    COALESCE(profit_factor,0) DESC,
                    COALESCE(expectancy,0) DESC,
                    queue_rank
                LIMIT 50;
            """)
            candidates = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_validation_queue_v1;")

            for idx, row in enumerate(candidates, start=1):
                validation_status, priority, recommended_action, risk_notes = status_for(row)

                evidence_summary = (
                    f"Trades={row.get('trades') or 0}; "
                    f"PF={row.get('profit_factor') or 0}; "
                    f"Expectancy={row.get('expectancy') or 0}; "
                    f"WinRate={row.get('winrate') or 0}; "
                    f"NetPnL={row.get('net_pnl') or 0}"
                )

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_validation_queue_v1 (
                        queue_rank,
                        symbol,
                        recommended_strategy_family AS strategy,
                        timeframe,
                        ''::text AS side,
                        candidate_status,
                        validation_status,
                        priority,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        evidence_summary,
                        risk_notes,
                        recommended_action,
                        source_queue_rank,
                        source_table,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("candidate_status") or "UNKNOWN",
                    validation_status,
                    priority,
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    evidence_summary,
                    risk_notes,
                    recommended_action,
                    row.get("queue_rank"),
                    row.get("source_table") or "",
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_validation_queue_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT validation_status, count(*) AS rows
                FROM marketcore_ui.edge_validation_queue_v1
                GROUP BY validation_status
                ORDER BY validation_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"status_{row['validation_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_QUEUE_V1_READY")


if __name__ == "__main__":
    main()
