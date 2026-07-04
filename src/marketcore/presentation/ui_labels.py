from __future__ import annotations


ROUTE_LABELS_RU = {
    "/": "Рабочий стол",

    "/paper-edge-discovery": "Edge",
    "/edge-validation-queue": "Проверка",
    "/edge-validation-pipeline": "Этапы",
    "/edge-robustness-check": "Устойчивость",
    "/edge-oos-validation": "Вне выборки",
    "/edge-oos-backtest": "Тест вне выборки",
    "/micro-live-readiness": "Проба",

    "/paper-edge-market-data-binding": "Данные",
    "/paper-edge-market-data-freshness": "Свежесть",
    "/paper-edge-market-symbol-alias-plan": "Alias",
    "/market-universe-ranking": "Рейтинг",
    "/market-universe-research-queue": "Кандидаты",
    "/market-universe-research-queue-timer-health": "Таймер Research",

    "/paper-sample-accumulation-monitor": "Выборка",
    "/paper-sample-collection-timer-health": "Таймер",
    "/paper-runtime-sample-collection-phase-close": "Фаза",
    "/phase-ii-paper-edge-discovery-summary": "Итоги",
    "/paper-runtime-sample-collection-operations": "Операции",
    "/paper-sample-operations-timer-health": "Таймер операций",
    "/paper-runtime-sample-collection-daily-summary": "Сводка",

    "/runtime": "Runtime",
    "/portfolio": "Портфель",
    "/orders": "Заявки",
    "/risk": "Риски",

    "/knowledge-graph": "Знания",
    "/research": "Исследования",
    "/validation": "Валидация",
    "/ai": "AI",

    "/logs": "Логи",
    "/system": "Система",
    "/settings": "Настройки",
    "/marketcore-ui-systemd-health": "UI",
    "/marketcore-ui-route-health-matrix": "Маршруты",
    "/edge-pipeline-v2": "Этапы V2",
    "edge_pipeline_v2.subtitle": "Единый снимок состояния кандидатов через Platform API.",
    "edge_pipeline_v2.total": "Всего",
    "edge_pipeline_v2.research": "Исследование",
    "edge_pipeline_v2.validation": "Проверка",
    "edge_pipeline_v2.robustness": "Устойчивость",
    "edge_pipeline_v2.oos": "OOS",
    "edge_pipeline_v2.risk": "Риск",
    "edge_pipeline_v2.trading": "Торговля",
    "edge_pipeline_v2.candidates": "Кандидаты",
    "edge_pipeline_v2.instrument": "Инструмент",
    "edge_pipeline_v2.asset": "Актив",
    "edge_pipeline_v2.strategy": "Стратегия",
    "edge_pipeline_v2.stage": "Этап",
    "edge_pipeline_v2.status": "Статус",
    "edge_pipeline_v2.priority": "Приоритет",
    "edge_pipeline_v2.backtest": "Бэктест",
}


def display_label(route: str, fallback: str = "") -> str:
    return ROUTE_LABELS_RU.get(route, fallback or route)


def route_labels() -> dict[str, str]:
    return dict(ROUTE_LABELS_RU)
