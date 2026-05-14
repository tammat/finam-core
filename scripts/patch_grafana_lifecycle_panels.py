from __future__ import annotations

import json
from pathlib import Path


DASHBOARD = Path("ops/grafana/dashboards/finam-mobile.json")
DATASOURCE_UID = "PBF3EFCF229E3034"


def next_panel_id(panels: list[dict]) -> int:
    return max([int(p.get("id", 0) or 0) for p in panels] or [0]) + 1


def add_table_panel(
    panels: list[dict],
    *,
    title: str,
    y: int,
    raw_sql: str,
) -> None:
    titles = {p.get("title") for p in panels}
    if title in titles:
        print(f"SKIP: {title}")
        return

    panels.append(
        {
            "id": next_panel_id(panels),
            "type": "table",
            "title": title,
            "datasource": {
                "type": "postgres",
                "uid": DATASOURCE_UID,
            },
            "gridPos": {
                "h": 8,
                "w": 24,
                "x": 0,
                "y": y,
            },
            "targets": [
                {
                    "refId": "A",
                    "format": "table",
                    "rawQuery": True,
                    "rawSql": raw_sql,
                }
            ],
            "options": {
                "showHeader": True,
                "cellHeight": "sm",
            },
            "fieldConfig": {
                "defaults": {},
                "overrides": [],
            },
        }
    )
    print(f"OK: added {title}")


def main() -> None:
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    panels = dashboard.setdefault("panels", [])

    add_table_panel(
        panels,
        title="Position Lifecycle State",
        y=124,
        raw_sql="""
SELECT
    updated_at AS "time",
    symbol,
    strategy,
    initial_qty,
    remaining_qty,
    tp1_done,
    tp2_done,
    profit_lock_done,
    trailing_active,
    current_stop,
    current_take_profit
FROM position_lifecycle_state
ORDER BY updated_at DESC
LIMIT 100
""",
    )

    add_table_panel(
        panels,
        title="Partial Close Status",
        y=132,
        raw_sql="""
SELECT
    updated_at AS "time",
    symbol,
    strategy,
    remaining_qty,
    tp1_done,
    tp2_done,
    current_stop,
    current_take_profit
FROM position_lifecycle_state
WHERE tp1_done = true
   OR tp2_done = true
ORDER BY updated_at DESC
LIMIT 100
""",
    )

    add_table_panel(
        panels,
        title="Active Trailing Stops",
        y=140,
        raw_sql="""
SELECT
    updated_at AS "time",
    symbol,
    strategy,
    remaining_qty,
    trailing_active,
    current_stop
FROM position_lifecycle_state
WHERE trailing_active = true
ORDER BY updated_at DESC
LIMIT 100
""",
    )

    add_table_panel(
        panels,
        title="Exit Lifecycle Audit",
        y=148,
        raw_sql="""
SELECT
    ts AS "time",
    symbol,
    action,
    qty,
    stop_price,
    reason,
    dry_run
FROM trailing_order_events
ORDER BY ts DESC
LIMIT 300
""",
    )

    dashboard["version"] = int(dashboard.get("version", 1)) + 1
    DASHBOARD.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
