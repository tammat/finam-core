from __future__ import annotations

import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import psycopg2
import psycopg2.extras

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route
from marketcore.presentation.ui_labels import display_label


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BASE_URL = os.getenv("MARKETCORE_UI_BASE_URL", "http://127.0.0.1:8080")
SOURCE_VERSION = "MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1"


def check_route(route: str) -> dict:
    url = BASE_URL.rstrip("/") + route

    try:
        with urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return {
            "http_status": int(exc.code),
            "http_ok": False,
            "contains_shell_marker": "MARKETCORE_UI_SHELL_V1" in body,
            "content_length": len(body),
            "issue": f"HTTPError:{exc.code}",
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "http_status": 0,
            "http_ok": False,
            "contains_shell_marker": False,
            "content_length": 0,
            "issue": f"{type(exc).__name__}:{exc}",
        }

    contains_shell_marker = "MARKETCORE_UI_SHELL_V1" in body
    http_ok = status == 200 and contains_shell_marker

    return {
        "http_status": status,
        "http_ok": http_ok,
        "contains_shell_marker": contains_shell_marker,
        "content_length": len(body),
        "issue": "" if http_ok else "missing shell marker or non-200",
    }


def main() -> None:
    build_id = str(uuid.uuid4())
    pages = menu_pages()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.marketcore_ui_route_health_matrix_v1;")

            unhealthy = 0

            for page in pages:
                group = group_for_route(page.route)
                result = check_route(page.route)

                if not result["http_ok"]:
                    unhealthy += 1

                cur.execute("""
                    INSERT INTO marketcore_ui.marketcore_ui_route_health_matrix_v1 (
                        route,
                        label_ru,
                        group_key,
                        group_title_ru,
                        menu_order,
                        http_status,
                        http_ok,
                        contains_shell_marker,
                        content_length,
                        issue,
                        checked_at,
                        source_version,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s
                    );
                """, (
                    page.route,
                    display_label(page.route, page.title),
                    group.key,
                    group.title_ru,
                    page.menu_order,
                    result["http_status"],
                    result["http_ok"],
                    result["contains_shell_marker"],
                    result["content_length"],
                    result["issue"],
                    SOURCE_VERSION,
                    build_id,
                ))

                print(
                    "ROUTE "
                    f"route={page.route} "
                    f"label={display_label(page.route, page.title)} "
                    f"group={group.key} "
                    f"http_status={result['http_status']} "
                    f"http_ok={int(result['http_ok'])} "
                    f"content_length={result['content_length']} "
                    f"issue={result['issue']}"
                )

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.marketcore_ui_route_health_matrix_v1;")
            rows_written = int(cur.fetchone()["rows"])

    print(f"routes_total={len(pages)}")
    print(f"rows_written={rows_written}")
    print(f"unhealthy_routes={unhealthy}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_V1_READY")


if __name__ == "__main__":
    main()
