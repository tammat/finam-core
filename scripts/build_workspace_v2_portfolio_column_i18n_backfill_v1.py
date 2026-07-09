from __future__ import annotations

import re
from typing import Any

import psycopg2
import psycopg2.extras


SOURCE_VERSION = "WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1"

SOURCE_VIEWS = (
    "public.v_real_portfolio_summary_ru",
    "public.v_real_portfolio_positions_ru",
    "public.v_positions_dashboard_ru",
    "public.v_portfolio_visualization_ru",
)


def normalize_column_key(column_name: str) -> str:
    return f"portfolio.column.{column_name.strip().lower()}"


def caption_from_column(column_name: str) -> str:
    text = re.sub(r"_+", " ", column_name.strip())
    text = text[:1].upper() + text[1:]
    return text


def fetch_columns(cur: Any, full_view_name: str) -> list[str]:
    schema_name, view_name = full_view_name.split(".", 1)
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema=%s
          AND table_name=%s
        ORDER BY ordinal_position
        """,
        (schema_name, view_name),
    )
    return [str(row["column_name"]) for row in cur.fetchall()]


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            all_columns: set[str] = set()

            for view_name in SOURCE_VIEWS:
                for column_name in fetch_columns(cur, view_name):
                    all_columns.add(column_name)

            inserted = 0

            for column_name in sorted(all_columns):
                resource_key = normalize_column_key(column_name)
                caption = caption_from_column(column_name)
                caption_short = caption
                caption_mobile = caption[:12]

                cur.execute(
                    """
                    INSERT INTO presentation.ui_resource_v1
                    (
                        resource_key,
                        locale_code,
                        caption,
                        caption_short,
                        caption_mobile,
                        tooltip,
                        icon,
                        resource_group
                    )
                    VALUES (%s,'ru',%s,%s,%s,%s,'','workspace_v2_portfolio_column')
                    ON CONFLICT(resource_key, locale_code)
                    DO UPDATE SET
                        caption=EXCLUDED.caption,
                        caption_short=EXCLUDED.caption_short,
                        caption_mobile=EXCLUDED.caption_mobile,
                        tooltip=EXCLUDED.tooltip,
                        icon=EXCLUDED.icon,
                        resource_group=EXCLUDED.resource_group
                    """,
                    (
                        resource_key,
                        caption,
                        caption_short,
                        caption_mobile,
                        f"Колонка портфеля: {caption}",
                    ),
                )
                inserted += 1

    print("=== WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1 ===")
    print(f"columns_total={inserted}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKSPACE_V2_PORTFOLIO_COLUMN_I18N_BACKFILL_V1_READY")


if __name__ == "__main__":
    main()
