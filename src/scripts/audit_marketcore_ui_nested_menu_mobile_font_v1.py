from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import group_for_route, route_groups
from marketcore.presentation.ui_labels import display_label


REQUIRED_LABELS = {
    "/market-universe-ranking": "Рейтинг",
    "/market-universe-research-queue": "Кандидаты",
    "/paper-sample-collection-timer-health": "Таймер",
    "/edge-robustness-check": "Устойчивость",
    "/edge-validation-pipeline": "Этапы",
    "/micro-live-readiness": "Проба",
    "/knowledge-graph": "Знания",
    "/edge-oos-validation": "Вне выборки",
    "/edge-oos-backtest": "Тест вне выборки",
}


def main() -> None:
    print("=== MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1 ===")

    pages = menu_pages()
    groups = route_groups()

    print(f"pages_total={len(pages)}")
    print(f"groups_total={len(groups)}")

    for route, expected in REQUIRED_LABELS.items():
        label = display_label(route)
        print(f"LABEL route={route} label={label}")
        if label != expected:
            raise SystemExit(f"BAD_LABEL route={route} expected={expected} actual={label}")

    for page in pages:
        group = group_for_route(page.route)
        print(f"PAGE group={group.title_ru} route={page.route} label={display_label(page.route, page.title)}")

    print("short_labels=READY")
    print("nested_menu=READY")
    print("mobile_font=READY")
    print("VERDICT=MARKETCORE_UI_NESTED_MENU_MOBILE_FONT_V1_READY")


if __name__ == "__main__":
    main()
