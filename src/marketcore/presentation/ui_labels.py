from __future__ import annotations


ROUTE_LABELS_RU = {
    "/": "Рабочий стол",

    "/runtime": "Runtime",
    "/paper-edge-discovery": "Поиск Edge",
    "/edge-validation-queue": "Очередь валидации Edge",
    "/edge-validation-pipeline": "Pipeline валидации",
    "/edge-robustness-check": "Проверка устойчивости",
    "/edge-oos-validation": "OOS-проверка",
    "/edge-oos-backtest": "OOS-бэктест",
    "/micro-live-readiness": "Готовность Micro Live",

    "/paper-sample-accumulation-monitor": "Накопление выборки",
    "/paper-sample-collection-timer-health": "Здоровье таймера выборки",
    "/paper-runtime-sample-collection-phase-close": "Закрытие фазы выборки",
    "/phase-ii-paper-edge-discovery-summary": "Итоги Phase II",
    "/paper-runtime-sample-collection-operations": "Операции накопления выборки",
    "/paper-sample-operations-timer-health": "Здоровье таймера операций",
    "/paper-runtime-sample-collection-daily-summary": "Дневная сводка операций",
    "/marketcore-ui-systemd-health": "Здоровье UI/Systemd",

    "/knowledge-graph": "Граф знаний",
    "/research": "Исследования",
    "/portfolio": "Портфель",
    "/orders": "Заявки",
    "/risk": "Риски",
    "/validation": "Валидация",
    "/logs": "Журнал",
    "/system": "Система",
    "/settings": "Настройки",
    "/ai": "AI",

    "/capital": "Капитал",
    "/edge": "Edge",
    "/intraday": "Интрадей",
}


def display_label(route: str, fallback: str = "") -> str:
    return ROUTE_LABELS_RU.get(route, fallback or route)


def route_labels() -> dict[str, str]:
    return dict(ROUTE_LABELS_RU)
