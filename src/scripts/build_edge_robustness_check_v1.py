from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_ROBUSTNESS_CHECK_V1"


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def normalize_winrate(value) -> Decimal:
    wr = dec(value)
    if wr > Decimal("1"):
        return wr / Decimal("100")
    return wr


def classify(row: dict) -> dict:
    trades = int(row.get("trades") or 0)
    pf = dec(row.get("profit_factor"))
    expectancy = dec(row.get("expectancy"))
    winrate = normalize_winrate(row.get("winrate"))
    net_pnl = dec(row.get("net_pnl"))

    sample_size_status = "PASS" if trades >= 30 else "WAIT_SAMPLE"

    if pf >= Decimal("1.2"):
        pf_status = "PASS"
    elif pf >= Decimal("1.0"):
        pf_status = "WATCH"
    else:
        pf_status = "FAIL"

    if expectancy > Decimal("0"):
        expectancy_status = "PASS"
    elif expectancy == Decimal("0"):
        expectancy_status = "WATCH"
    else:
        expectancy_status = "FAIL"

    if winrate >= Decimal("0.50"):
        winrate_status = "PASS"
    elif winrate >= Decimal("0.45"):
        winrate_status = "WATCH"
    else:
        winrate_status = "FAIL"

    pnl_status = "PASS" if net_pnl > Decimal("0") else "FAIL"

    sample_score = Decimal("1") if sample_size_status == "PASS" else Decimal("0")
    pf_score = Decimal("1") if pf_status == "PASS" else Decimal("0.5") if pf_status == "WATCH" else Decimal("0")
    exp_score = Decimal("1") if expectancy_status == "PASS" else Decimal("0.5") if expectancy_status == "WATCH" else Decimal("0")
    wr_score = Decimal("1") if winrate_status == "PASS" else Decimal("0.5") if winrate_status == "WATCH" else Decimal("0")
    pnl_score = Decimal("1") if pnl_status == "PASS" else Decimal("0")

    robustness_score = (
        sample_score * Decimal("0.25")
        + pf_score * Decimal("0.25")
        + exp_score * Decimal("0.25")
        + wr_score * Decimal("0.15")
        + pnl_score * Decimal("0.10")
    )

    if trades < 30:
        robustness_status = "WAIT_SAMPLE"
        recommended_action = "Накопить выборку Paper Runtime до 30+ сделок."
        weakness_summary = "Недостаточная выборка для robustness-проверки."
        oos_required = False
    elif pf >= Decimal("1.2") and expectancy > Decimal("0") and winrate >= Decimal("0.45"):
        robustness_status = "ROBUSTNESS_REQUIRED"
        recommended_action = "Запустить robustness-проверку по времени, режимам рынка и параметрам."
        weakness_summary = "До продвижения требуется проверить устойчивость и OOS."
        oos_required = True
    elif pf >= Decimal("1.0") and expectancy >= Decimal("0"):
        robustness_status = "WATCHLIST"
        recommended_action = "Продолжить наблюдение и проверить устойчивость после накопления новых сделок."
        weakness_summary = "Преимущество слабое или недостаточно устойчивое."
        oos_required = False
    else:
        robustness_status = "ROBUSTNESS_REJECT"
        recommended_action = "Не продвигать кандидата без улучшения статистики."
        weakness_summary = "Статистика не подтверждает устойчивый edge."
        oos_required = False

    evidence_summary = (
        f"Trades={trades}; "
        f"PF={pf}; "
        f"Expectancy={expectancy}; "
        f"WinRate={winrate}; "
        f"NetPnL={net_pnl}; "
        f"Score={row.get('score') or 0}"
    )

    return {
        "sample_size_status": sample_size_status,
        "pf_status": pf_status,
        "expectancy_status": expectancy_status,
        "winrate_status": winrate_status,
        "pnl_status": pnl_status,
        "robustness_status": robustness_status,
        "robustness_score": robustness_score,
        "oos_required": oos_required,
        "micro_live_ready": False,
        "evidence_summary": evidence_summary,
        "weakness_summary": weakness_summary,
        "recommended_action": recommended_action,
    }


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_ROBUSTNESS_CHECK_V1 ===")

            cur.execute("""
                SELECT
                    pipeline_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    pipeline_status,
                    expectancy,
                    profit_factor,
                    winrate,
                    trades,
                    net_pnl,
                    score,
                    evidence_summary,
                    risk_notes
                FROM marketcore_ui.edge_validation_pipeline_v1
                ORDER BY
                    CASE
                        WHEN pipeline_status='READY_FOR_ROBUSTNESS' THEN 1
                        WHEN pipeline_status='OBSERVE_MORE' THEN 2
                        WHEN pipeline_status='ACCUMULATE_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    pipeline_rank;
            """)
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_robustness_check_v1;")

            for idx, row in enumerate(rows, start=1):
                c = classify(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_robustness_check_v1 (
                        robustness_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        pipeline_status,
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
                        recommended_action,
                        source_pipeline_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
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
                    row.get("pipeline_status") or "UNKNOWN",
                    c["robustness_status"],
                    c["sample_size_status"],
                    c["pf_status"],
                    c["expectancy_status"],
                    c["winrate_status"],
                    c["pnl_status"],
                    c["robustness_score"],
                    c["oos_required"],
                    c["micro_live_ready"],
                    row.get("expectancy"),
                    row.get("profit_factor"),
                    row.get("winrate"),
                    row.get("trades"),
                    row.get("net_pnl"),
                    row.get("score"),
                    c["evidence_summary"],
                    c["weakness_summary"],
                    c["recommended_action"],
                    row.get("pipeline_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_robustness_check_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT robustness_status, count(*) AS rows
                FROM marketcore_ui.edge_robustness_check_v1
                GROUP BY robustness_status
                ORDER BY robustness_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"robustness_status_{row['robustness_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY")


if __name__ == "__main__":
    main()
