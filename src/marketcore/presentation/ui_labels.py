from __future__ import annotations


ROUTE_LABELS_RU = {
    "/": "Рабочий стол",

    "/runtime": "Runtime / исполнение",
    "/paper-edge-discovery": "Поиск преимущества",
    "/paper-edge-market-data-binding": "Рыночные данные кандидатов",
    "/paper-edge-market-data-freshness": "Свежесть рыночных данных",
    "/paper-edge-market-symbol-alias-plan": "План alias рыночных символов",
    "/edge-validation-queue": "Очередь проверки преимущества",
    "/edge-validation-pipeline": "Pipeline проверки преимущества",
    "/edge-robustness-check": "Проверка устойчивости",
    "/edge-oos-validation": "Вневыборочная проверка",
    "/edge-oos-backtest": "Вневыборочный бэктест",
    "/micro-live-readiness": "Готовность Micro Live",

    "/paper-sample-accumulation-monitor": "Накопление выборки",
    "/paper-sample-collection-timer-health": "Здоровье таймера выборки",
    "/paper-runtime-sample-collection-phase-close": "Закрытие фазы выборки",
    "/phase-ii-paper-edge-discovery-summary": "Итоги Phase II: поиск преимущества",
    "/paper-runtime-sample-collection-operations": "Операции накопления выборки",
    "/paper-sample-operations-timer-health": "Здоровье таймера операций",
    "/paper-runtime-sample-collection-daily-summary": "Дневная сводка операций выборки",
    "/marketcore-ui-systemd-health": "Здоровье UI и systemd",
    "/marketcore-ui-route-health-matrix": "Матрица маршрутов UI",

    "/knowledge-graph": "Граф знаний",
    "/research": "Исследования",
    "/portfolio": "Портфель",
    "/orders": "Заявки",
    "/risk": "Риски",
    "/validation": "Валидация",
    "/logs": "Журнал",
    "/system": "Система",
    "/settings": "Настройки",
    "/ai": "AI / помощник",

    "/capital": "Капитал",
    "/edge": "Преимущество",
    "/intraday": "Интрадей",
}


def display_label(route: str, fallback: str = "") -> str:
    return ROUTE_LABELS_RU.get(route, fallback or route)


def route_labels() -> dict[str, str]:
    return dict(ROUTE_LABELS_RU)
