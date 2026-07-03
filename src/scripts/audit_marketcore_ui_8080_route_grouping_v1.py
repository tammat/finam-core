from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route, route_groups
from marketcore.presentation.ui_labels import display_label


REQUIRED_GROUPS = {
    "home",
    "paper_edge",
    "sample_collection",
    "knowledge_platform",
    "trading_control",
    "system",
}

REQUIRED_ROUTE_GROUPS = {
    "/": "home",
    "/paper-edge-discovery": "paper_edge",
    "/edge-validation-queue": "paper_edge",
    "/edge-validation-pipeline": "paper_edge",
    "/edge-robustness-check": "paper_edge",
    "/edge-oos-validation": "paper_edge",
    "/edge-oos-backtest": "paper_edge",
    "/micro-live-readiness": "paper_edge",
    "/paper-sample-accumulation-monitor": "sample_collection",
    "/paper-runtime-sample-collection-operations": "sample_collection",
    "/paper-runtime-sample-collection-daily-summary": "sample_collection",
    "/phase-ii-paper-edge-discovery-summary": "sample_collection",
    "/knowledge-graph": "knowledge_platform",
    "/research": "knowledge_platform",
    "/validation": "knowledge_platform",
    "/runtime": "trading_control",
    "/portfolio": "trading_control",
    "/orders": "trading_control",
    "/risk": "trading_control",
    "/logs": "system",
    "/system": "system",
    "/settings": "system",
    "/marketcore-ui-systemd-health": "system",
}


def main() -> None:
    pages = menu_pages()
    group_keys = {group.key for group in route_groups()}
    missing_groups = sorted(REQUIRED_GROUPS - group_keys)

    print("=== MARKETCORE_UI_8080_ROUTE_GROUPING_V1 ===")
    print(f"pages_total={len(pages)}")
    print(f"groups_total={len(group_keys)}")

    if missing_groups:
        print("missing_groups=" + ",".join(missing_groups))
        raise SystemExit(2)

    page_routes = {page.route for page in pages}
    missing_routes = sorted(set(REQUIRED_ROUTE_GROUPS) - page_routes)

    if missing_routes:
        print("missing_routes=" + ",".join(missing_routes))
        raise SystemExit(3)

    unknown_routes: list[str] = []
    wrong_groups: list[str] = []

    for page in pages:
        group = group_for_route(page.route)
        label = display_label(page.route, page.title)

        print(
            "PAGE "
            f"group={group.key} "
            f"group_title={group.title_ru} "
            f"route={page.route} "
            f"label_ru={label} "
            f"order={page.menu_order}"
        )

        if group.key == "other":
            unknown_routes.append(page.route)

        expected_group = REQUIRED_ROUTE_GROUPS.get(page.route)
        if expected_group and expected_group != group.key:
            wrong_groups.append(f"{page.route}:{group.key}!={expected_group}")

    if unknown_routes:
        print("unknown_routes=" + ",".join(sorted(unknown_routes)))
        raise SystemExit(4)

    if wrong_groups:
        print("wrong_groups=" + ",".join(sorted(wrong_groups)))
        raise SystemExit(5)

    print("route_groups_required=READY")
    print("route_grouping_complete=READY")
    print("route_grouping_no_unknown_routes=READY")
    print("route_grouping_ru_titles=READY")
    print("VERDICT=MARKETCORE_UI_8080_ROUTE_GROUPING_V1_READY")


if __name__ == "__main__":
    main()
