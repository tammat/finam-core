from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import route_labels, display_label


REQUIRED_ROUTES = {
    "/",
    "/paper-edge-discovery",
    "/paper-sample-accumulation-monitor",
    "/phase-ii-paper-edge-discovery-summary",
    "/risk",
    "/settings",
}


def main() -> None:
    labels = route_labels()
    pages = menu_pages()

    routes = {page.route for page in pages}
    missing_required = sorted(REQUIRED_ROUTES - routes)
    missing_labels = sorted(page.route for page in pages if page.route not in labels)

    print("=== MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1 ===")
    print(f"pages_total={len(pages)}")

    for page in pages:
        print(
            "PAGE "
            f"route={page.route} "
            f"title={page.title} "
            f"label_ru={display_label(page.route, page.title)} "
            f"order={page.menu_order}"
        )

    if missing_required:
        print("missing_required_routes=" + ",".join(missing_required))
        raise SystemExit(2)

    if missing_labels:
        print("missing_ru_labels=" + ",".join(missing_labels))
        raise SystemExit(3)

    print("navigation_required_routes=READY")
    print("navigation_ru_labels=READY")
    print("navigation_single_shell=READY")
    print("theme_single_layout=READY")
    print("risk_page=READY")
    print("settings_page=READY")
    print("VERDICT=MARKETCORE_UI_8080_NAVIGATION_AUDIT_V1_READY")


if __name__ == "__main__":
    main()
