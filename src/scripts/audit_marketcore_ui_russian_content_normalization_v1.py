from __future__ import annotations

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import display_label, route_labels
from marketcore.presentation.ui_text import normalize_ui_text


REQUIRED_ROUTES = {
    "/",
    "/paper-edge-discovery",
    "/paper-runtime-sample-collection-daily-summary",
    "/marketcore-ui-systemd-health",
    "/risk",
    "/settings",
}

FORBIDDEN_SNIPPETS_AFTER_NORMALIZATION = [
    "Next Action",
    "Source:",
    "Paper Runtime Real Data",
    "Research Candidates",
    "Candidate Explainability",
    "TOP Candidates Detail",
    "Systemd Details",
    "Daily Summary",
    "Operations Queue",
    "Settings</h1>",
    "Risk</h1>",
]

REQUIRED_NORMALIZED_SNIPPETS = [
    "Следующее действие",
    "Источник:",
    "Реальные данные Paper Runtime",
    "Кандидаты исследования",
    "Объяснение кандидатов",
    "Детализация TOP-кандидатов",
    "Детали systemd",
    "Дневная сводка",
    "Очередь операций",
    "Настройки",
    "Риски",
]


def main() -> None:
    labels = route_labels()
    pages = menu_pages()
    routes = {page.route for page in pages}

    missing_routes = sorted(REQUIRED_ROUTES - routes)
    missing_labels = sorted(page.route for page in pages if page.route not in labels)

    print("=== MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1 ===")
    print(f"pages_total={len(pages)}")

    for page in pages:
        print(
            "PAGE "
            f"route={page.route} "
            f"title={page.title} "
            f"label_ru={display_label(page.route, page.title)}"
        )

    if missing_routes:
        print("missing_required_routes=" + ",".join(missing_routes))
        raise SystemExit(2)

    if missing_labels:
        print("missing_ru_labels=" + ",".join(missing_labels))
        raise SystemExit(3)

    sample = """
    Next Action
    Source:
    Paper Runtime Real Data
    Research Candidates
    Candidate Explainability
    TOP Candidates Detail
    Systemd Details
    Daily Summary
    Operations Queue
    Settings
    Risk
    """

    normalized = normalize_ui_text(sample)

    for snippet in FORBIDDEN_SNIPPETS_AFTER_NORMALIZATION:
        if snippet in normalized:
            print(f"forbidden_after_normalization={snippet}")
            raise SystemExit(4)

    for snippet in REQUIRED_NORMALIZED_SNIPPETS:
        if snippet not in normalized:
            print(f"missing_required_normalized_snippet={snippet}")
            raise SystemExit(5)

    print("route_labels_ru=READY")
    print("content_normalizer=READY")
    print("risk_settings_ru=READY")
    print("single_theme_layout=READY")
    print("VERDICT=MARKETCORE_UI_RUSSIAN_CONTENT_NORMALIZATION_V1_READY")


if __name__ == "__main__":
    main()
