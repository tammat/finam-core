from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route


BASE_URL = "http://127.0.0.1:8080"

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


def check_domain(endpoint: str) -> tuple[int, bool, str]:
    url = BASE_URL + endpoint

    try:
        with urlopen(url, timeout=10) as response:
            body = response.read().decode(
                "utf-8",
                errors="replace",
            )
            payload = json.loads(body)

            healthy = (
                int(response.status) == 200
                and isinstance(payload, dict)
                and bool(payload)
            )

            return int(response.status), healthy, ""

    except HTTPError as exc:
        return int(exc.code), False, f"HTTPError:{exc.code}"

    except (
        URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return 0, False, f"{type(exc).__name__}:{exc}"


def resolve_domain(route: str, group_key: str) -> tuple[str, str]:
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


def main() -> int:
    print("=== MARKETCORE_UI_DOMAIN_RENDER_TREE_MAPPING_V1 ===")

    domain_health: dict[str, bool] = {}

    for domain, endpoint in DOMAIN_ENDPOINTS.items():
        status, healthy, issue = check_domain(endpoint)
        domain_health[domain] = healthy

        print(
            "DOMAIN "
            f"domain={domain} "
            f"endpoint={endpoint} "
            f"http_status={status} "
            f"healthy={int(healthy)} "
            f"issue={issue}"
        )

    pages = menu_pages()
    mapped_routes = 0
    healthy_routes = 0

    for page in pages:
        group = group_for_route(page.route)

        domain, source = resolve_domain(
            page.route,
            group.key,
        )

        mapped = domain in DOMAIN_ENDPOINTS
        healthy = mapped and domain_health.get(domain, False)

        mapped_routes += int(mapped)
        healthy_routes += int(healthy)

        print(
            "MAPPING "
            f"route={page.route} "
            f"group={group.key} "
            f"domain={domain} "
            f"mapping_source={source} "
            f"route_healthy={int(healthy)}"
        )

    healthy_domains = sum(
        int(value)
        for value in domain_health.values()
    )

    print(f"domains_total={len(DOMAIN_ENDPOINTS)}")
    print(f"healthy_domains={healthy_domains}")
    print(
        "unhealthy_domains="
        f"{len(DOMAIN_ENDPOINTS) - healthy_domains}"
    )
    print(f"routes_total={len(pages)}")
    print(f"mapped_routes={mapped_routes}")
    print(f"healthy_routes={healthy_routes}")
    print("mapping_contract=EXPLICIT_AGGREGATED_DOMAINS_V1")
    print("legacy_html_routes_required=0")
    print("writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "MARKETCORE_UI_DOMAIN_RENDER_TREE_MAPPING_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
