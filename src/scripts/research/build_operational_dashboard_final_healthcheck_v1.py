#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[3]


def check_db() -> dict:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    count(*) as rows,
                    count(*) filter (where operational_status='OPEN_PAPER_LONG_TAIL') as open_rows,
                    count(*) filter (where operational_status='CLEAN_V3_FLAT') as flat_rows,
                    count(*) filter (where operational_status='CLEAN_V3_OPEN_REVIEW') as open_review_rows,
                    count(*) filter (where operational_status='QUARANTINE_CONTAMINATED_TAIL') as quarantine_rows,
                    count(*) filter (where operational_status='EXCLUDE_HISTORICAL_TAIL') as excluded_rows,
                    count(*) filter (where is_current_operational_position=true) as current_position_rows,
                    count(*) filter (where include_in_clean_operational_view=true) as included_rows
                from clean_operational_position_view_v1;
            """)
            view_row = dict(cur.fetchone())

            cur.execute("""
                select
                    current_position_count,
                    clean_flat_count,
                    clean_open_review_count,
                    quarantine_count,
                    excluded_count,
                    current_net_qty_sum,
                    included_rows,
                    excluded_or_quarantined_rows,
                    included_v3_pnl
                from clean_operational_position_metrics_v1;
            """)
            metrics_row = dict(cur.fetchone())

    return {
        "view": view_row,
        "metrics": metrics_row,
    }


def check_jinja() -> int:
    template_dir = ROOT / "src/ui/templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    tpl = env.get_template("v3_dashboard.html")

    html = tpl.render(
        request=None,
        data={
            "title": "TEST",
            "mode": "TEST",
            "runtime": "Закрыт",
            "execution": "Закрыто",
            "summary": {
                "strategies": 0,
                "clean_trades": 0,
                "v3_full_chains": 0,
                "v3_pnl": 0,
            },
            "accumulation": [],
            "statistics": [],
            "daily": [],
            "checkpoints": [],
        },
        active="v3",
        operational_positions_error_v1=None,
        operational_metrics_error_v1=None,
        operational_metrics_v1={
            "current_position_count": 1,
            "clean_flat_count": 5,
            "clean_open_review_count": 1,
            "quarantine_count": 1,
            "excluded_count": 1,
            "current_net_qty_sum": 5,
        },
        operational_positions_v1=[
            {
                "symbol": "BRN6@RTSX",
                "strategy": "BR_CONSERVATIVE_BREAKOUT",
                "timeframe": "M5",
                "net_qty": 5,
                "full_chains": 102,
                "pnl": -124.211906,
                "operational_status": "OPEN_PAPER_LONG_TAIL",
            },
            {
                "symbol": "NGQ6@RTSX",
                "strategy": "NG_CONSERVATIVE_BREAKOUT_M1",
                "timeframe": "M1",
                "net_qty": 0,
                "full_chains": 11,
                "pnl": -0.045360,
                "operational_status": "CLEAN_V3_FLAT",
            },
            {
                "symbol": "USDRUBF@RTSX",
                "strategy": "USD_INTRADAY_REGIME",
                "timeframe": "M5",
                "net_qty": 3,
                "full_chains": 7,
                "pnl": -0.508082,
                "operational_status": "QUARANTINE_CONTAMINATED_TAIL",
            },
        ],
    )

    required = [
        "Операционное состояние paper-позиций",
        "Текущих paper-позиций",
        "Текущий net qty",
        "Текущая paper-позиция",
        "Clean V3 без открытой позиции",
        "Карантин",
        "Исключено из operational state",
    ]

    missing = [x for x in required if x not in html]
    if missing:
        raise RuntimeError("Jinja render missing markers: " + ", ".join(missing))

    return len(html)


def main() -> int:
    print("=== OPERATIONAL DASHBOARD FINAL HEALTHCHECK V1 ===")
    print("mode=healthcheck")
    print("runtime_allow=0")
    print("execution_enabled=0")

    db = check_db()
    view = db["view"]
    metrics = db["metrics"]

    print(
        "DB_VIEW_ROW "
        f"rows={view['rows']} "
        f"open_rows={view['open_rows']} "
        f"flat_rows={view['flat_rows']} "
        f"open_review_rows={view['open_review_rows']} "
        f"quarantine_rows={view['quarantine_rows']} "
        f"excluded_rows={view['excluded_rows']} "
        f"current_position_rows={view['current_position_rows']} "
        f"included_rows={view['included_rows']}"
    )

    print(
        "DB_METRICS_ROW "
        f"current_position_count={metrics['current_position_count']} "
        f"clean_flat_count={metrics['clean_flat_count']} "
        f"clean_open_review_count={metrics['clean_open_review_count']} "
        f"quarantine_count={metrics['quarantine_count']} "
        f"excluded_count={metrics['excluded_count']} "
        f"current_net_qty_sum={metrics['current_net_qty_sum']} "
        f"included_rows={metrics['included_rows']} "
        f"excluded_or_quarantined_rows={metrics['excluded_or_quarantined_rows']} "
        f"included_v3_pnl={metrics['included_v3_pnl']}"
    )

    current_position_count = int(metrics["current_position_count"] or 0)
    clean_flat_count = int(metrics["clean_flat_count"] or 0)
    clean_open_review_count = int(metrics["clean_open_review_count"] or 0)
    included_rows = int(metrics["included_rows"] or 0)

    expected_included = current_position_count + clean_flat_count + clean_open_review_count

    failures: list[str] = []

    if int(metrics["quarantine_count"] or 0) != 1:
        failures.append("quarantine_count_not_1")

    if int(metrics["excluded_count"] or 0) != 1:
        failures.append("excluded_count_not_1")

    if included_rows != expected_included:
        failures.append(f"included_rows_mismatch={included_rows}_expected={expected_included}")

    if int(view["current_position_rows"] or 0) != current_position_count:
        failures.append("view_current_position_rows_mismatch")

    if int(view["quarantine_rows"] or 0) != int(metrics["quarantine_count"] or 0):
        failures.append("view_quarantine_rows_mismatch")

    if int(view["excluded_rows"] or 0) != int(metrics["excluded_count"] or 0):
        failures.append("view_excluded_rows_mismatch")

    html_len = check_jinja()
    print(f"JINJA_RENDER_OK length={html_len}")

    if failures:
        print("VERDICT=OPERATIONAL_DASHBOARD_HEALTHCHECK_FAILED " + ",".join(failures))
        raise SystemExit(1)

    print("VERDICT=OPERATIONAL_DASHBOARD_FINAL_HEALTHCHECK_OK")
    print("OPERATIONAL_DASHBOARD_FINAL_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
