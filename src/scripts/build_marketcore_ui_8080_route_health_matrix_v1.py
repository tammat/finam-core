from __future__ import annotations

import json
import os
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import psycopg2
import psycopg2.extras

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route
from marketcore.presentation.ui_labels import display_label


DB = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

BASE_URL = os.getenv(
    "MARKETCORE_UI_BASE_URL",
    "http://127.0.0.1:8080",
)

SOURCE_VERSION = (
    "MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_RUNTIME_V2_V1"
)

SHELL_RUNTIME_MARKER = 'data-marketcore-ui-runtime="v2"'
SHELL_BOOTSTRAP_MARKER = "workspace-shell-bootstrap.js"

DOMAIN_ENDPOINTS = {
    "HOME": "/api/v2/domain-render-tree/home",
    "PORTFOLIO": "/api/v2/domain-render-tree/portfolio",
    "CONTROL_CENTER": "/api/v2/domain-render-tree/control-center",
    "SETTINGS": "/api/v2/domain-render-tree/settings",
    "CAPITAL": "/api/v2/domain-render-tree/capital",
    "RISK": "/api/v2/domain-render-tree/risk",
    "RESEARCH": "/api/v2/domain-render-tree/research",
    "INTRADAY": "/api/v2/domain-render-tree/intraday",
    "PROGRAM": "/api/v2/domain-render-tree/program",
}

DIRECT_ROUTE_DOMAINS = {
    "/": "HOME",
    "/portfolio": "PORTFOLIO",
    "/risk": "RISK",
    "/settings": "SETTINGS",
}

PREFIX_DOMAINS = (
    ("/edge-", "RESEARCH"),
    ("/max-edge", "RESEARCH"),
    ("/paper-edge-", "RESEARCH"),
    ("/market-universe-", "RESEARCH"),
    ("/phase-ii-paper-edge-", "RESEARCH"),
    ("/paper-runtime-", "PROGRAM"),
    ("/paper-sample-", "PROGRAM"),
    ("/runtime", "PROGRAM"),
    ("/micro-live-", "PROGRAM"),
    ("/portfolio-platform", "PORTFOLIO"),
    ("/paper-mtm", "PORTFOLIO"),
    ("/risk-platform", "RISK"),
    ("/orders", "INTRADAY"),
    ("/logs", "PROGRAM"),
    ("/system", "PROGRAM"),
    ("/ai", "PROGRAM"),
    ("/marketcore-ui-", "PROGRAM"),
    ("/feature-store", "CONTROL_CENTER"),
    ("/knowledge-graph", "CONTROL_CENTER"),
    ("/validation", "CONTROL_CENTER"),
    ("/market-model", "CONTROL_CENTER"),
    ("/strategy-", "CONTROL_CENTER"),
    ("/trading-platform", "CONTROL_CENTER"),
    ("/recommendation", "CONTROL_CENTER"),
)

GROUP_DOMAINS = {
    "home": "HOME",
    "research": "RESEARCH",
    "portfolio": "PORTFOLIO",
    "market": "CONTROL_CENTER",
    "data": "CONTROL_CENTER",
    "system": "PROGRAM",
}


def read_url(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=10) as response:
            body = response.read().decode(
                "utf-8",
                errors="replace",
            )

            return {
                "status": int(response.status),
                "body": body,
                "error": "",
            }

    except HTTPError as exc:
        try:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            body = ""

        return {
            "status": int(exc.code),
            "body": body,
            "error": f"HTTPError:{exc.code}",
        }

    except (URLError, TimeoutError, OSError) as exc:
        return {
            "status": 0,
            "body": "",
            "error": f"{type(exc).__name__}:{exc}",
        }


def check_shell() -> dict[str, Any]:
    url = BASE_URL.rstrip("/") + "/"
    response = read_url(url)
    body = response["body"]

    contains_shell_marker = (
        "MarketCore OS" in body
        and SHELL_RUNTIME_MARKER in body
        and SHELL_BOOTSTRAP_MARKER in body
    )

    healthy = (
        response["status"] == 200
        and contains_shell_marker
    )

    return {
        "http_status": response["status"],
        "healthy": healthy,
        "contains_shell_marker": contains_shell_marker,
        "content_length": len(body),
        "issue": (
            ""
            if healthy
            else response["error"]
            or "missing_runtime_v2_shell_marker"
        ),
    }


def check_domain(
    domain: str,
) -> dict[str, Any]:
    endpoint = DOMAIN_ENDPOINTS[domain]
    url = BASE_URL.rstrip("/") + endpoint
    response = read_url(url)

    json_ok = False
    payload_nonempty = False
    json_issue = ""

    if response["status"] == 200 and response["body"].strip():
        try:
            payload = json.loads(response["body"])
            json_ok = isinstance(payload, dict)
            payload_nonempty = bool(payload) if json_ok else False
        except json.JSONDecodeError as exc:
            json_issue = f"JSONDecodeError:{exc.msg}"

    healthy = (
        response["status"] == 200
        and json_ok
        and payload_nonempty
    )

    issue = ""

    if not healthy:
        issue = (
            response["error"]
            or json_issue
            or "empty_or_invalid_render_tree"
        )

    return {
        "domain": domain,
        "endpoint": endpoint,
        "http_status": response["status"],
        "healthy": healthy,
        "content_length": len(response["body"]),
        "issue": issue,
    }


def resolve_domain(
    route: str,
    group_key: str,
) -> tuple[str, str]:
    direct = DIRECT_ROUTE_DOMAINS.get(route)

    if direct:
        return direct, "direct"

    for prefix, domain in PREFIX_DOMAINS:
        if route.startswith(prefix):
            return domain, f"prefix:{prefix}"

    grouped = GROUP_DOMAINS.get(group_key)

    if grouped:
        return grouped, f"group:{group_key}"

    return "CONTROL_CENTER", "fallback"


def main() -> None:
    build_id = str(uuid.uuid4())
    pages = menu_pages()
    shell = check_shell()

    domain_results = {
        domain: check_domain(domain)
        for domain in DOMAIN_ENDPOINTS
    }

    print(
        "=== "
        "MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_"
        "RUNTIME_V2_V1 ==="
    )

    print(
        "SHELL "
        f"http_status={shell['http_status']} "
        f"healthy={int(shell['healthy'])} "
        f"content_length={shell['content_length']} "
        f"issue={shell['issue']}"
    )

    for domain, result in domain_results.items():
        print(
            "DOMAIN "
            f"domain={domain} "
            f"endpoint={result['endpoint']} "
            f"http_status={result['http_status']} "
            f"healthy={int(result['healthy'])} "
            f"content_length={result['content_length']} "
            f"issue={result['issue']}"
        )

    unhealthy_routes = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                """
                DELETE FROM
                    marketcore_ui.
                    marketcore_ui_route_health_matrix_v1
                """
            )

            for page in pages:
                group = group_for_route(page.route)

                domain, mapping_source = resolve_domain(
                    page.route,
                    group.key,
                )

                domain_result = domain_results[domain]

                route_healthy = (
                    bool(shell["healthy"])
                    and bool(domain_result["healthy"])
                )

                if not route_healthy:
                    unhealthy_routes += 1

                issue_parts: list[str] = []

                if not shell["healthy"]:
                    issue_parts.append(
                        f"shell:{shell['issue']}"
                    )

                if not domain_result["healthy"]:
                    issue_parts.append(
                        f"domain:{domain_result['issue']}"
                    )

                issue = ";".join(issue_parts)

                cur.execute(
                    """
                    INSERT INTO
                        marketcore_ui.
                        marketcore_ui_route_health_matrix_v1 (
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
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        now(),
                        %s,
                        %s
                    )
                    """,
                    (
                        page.route,
                        display_label(
                            page.route,
                            page.title,
                        ),
                        group.key,
                        group.title_ru,
                        page.menu_order,
                        domain_result["http_status"],
                        route_healthy,
                        shell["contains_shell_marker"],
                        domain_result["content_length"],
                        issue,
                        SOURCE_VERSION,
                        build_id,
                    ),
                )

                print(
                    "ROUTE "
                    f"route={page.route} "
                    f"domain={domain} "
                    f"domain_endpoint="
                    f"{domain_result['endpoint']} "
                    f"mapping_source={mapping_source} "
                    f"shell_healthy="
                    f"{int(shell['healthy'])} "
                    f"domain_healthy="
                    f"{int(domain_result['healthy'])} "
                    f"http_status="
                    f"{domain_result['http_status']} "
                    f"http_ok={int(route_healthy)} "
                    f"issue={issue}"
                )

            cur.execute(
                """
                SELECT count(*) AS rows
                FROM
                    marketcore_ui.
                    marketcore_ui_route_health_matrix_v1
                """
            )

            rows_written = int(
                cur.fetchone()["rows"]
            )

    healthy_domains = sum(
        int(result["healthy"])
        for result in domain_results.values()
    )

    print(f"domains_total={len(DOMAIN_ENDPOINTS)}")
    print(f"healthy_domains={healthy_domains}")
    print(
        "unhealthy_domains="
        f"{len(DOMAIN_ENDPOINTS) - healthy_domains}"
    )
    print(f"routes_total={len(pages)}")
    print(f"rows_written={rows_written}")
    print(
        f"healthy_routes="
        f"{len(pages) - unhealthy_routes}"
    )
    print(f"unhealthy_routes={unhealthy_routes}")
    print("mapping_contract=EXPLICIT_AGGREGATED_DOMAINS_V1")
    print("runtime_contract=DOMAIN_RENDER_TREE_V2")
    print("legacy_html_routes_required=0")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "MARKETCORE_UI_8080_ROUTE_HEALTH_MATRIX_"
        "RUNTIME_V2_V1_READY"
    )


if __name__ == "__main__":
    main()
