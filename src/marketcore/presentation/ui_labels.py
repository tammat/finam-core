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

try:
    ROUTE_LABELS_RU.update({
        "/edge-pipeline-v2": "Этапы V2",
        "/paper-edge-discovery": "Edge",
        "/edge-validation-queue": "Проверка",
        "/edge-validation-pipeline": "Этапы",
        "/edge-robustness-check": "Устойчивость",
        "/edge-oos-validation": "Вне выборки",
        "/edge-oos-backtest": "Тест вне выборки",
        "/micro-live-readiness": "Проба",
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "/strategy-workbench": "Рабочее место стратегии",
        "strategy.workbench.title": "Рабочее место стратегии",
        "strategy.workbench.subtitle": "Диагностика решений стратегии через Platform API.",
        "strategy.workbench.summary": "Сводка",
        "strategy.workbench.features_checked": "Проверено признаков",
        "strategy.workbench.signals_found": "Найдено сигналов",
        "strategy.workbench.strategy": "Стратегия",
        "strategy.workbench.rows": "Диагностика",
        "strategy.workbench.instrument": "Инструмент",
        "strategy.workbench.timeframe": "TF",
        "strategy.workbench.bar": "Бар",
        "strategy.workbench.signal": "Сигнал",
        "strategy.workbench.reason": "Причина",
        "strategy.workbench.score": "Score",
        "strategy.workbench.confidence": "Confidence",
        "strategy.workbench.passed": "Прошли",
        "strategy.workbench.failed": "Не прошли",
        "strategy.workbench.execution_time": "Время",
        "signal.LONG": "Long",
        "signal.SHORT": "Short",
        "signal.FLAT": "Нет сигнала",
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "/strategy-platform": "Платформа стратегий",

        "strategy.platform.title": "Платформа стратегий",
        "strategy.platform.subtitle": "Каталог, конфигурации, зависимости и сигналы стратегий через Platform API.",
        "strategy.platform.summary": "Сводка",
        "strategy.platform.registry": "Каталог стратегий",
        "strategy.platform.configuration": "Конфигурации",
        "strategy.platform.dependencies": "Зависимости от признаков",
        "strategy.platform.signals": "Последние сигналы",

        "strategy.platform.strategies_total": "Всего стратегий",
        "strategy.platform.strategies_enabled": "Включено",
        "strategy.platform.active_configs": "Активные конфигурации",
        "strategy.platform.signals_total": "Всего сигналов",
        "strategy.platform.health": "Здоровье",
        "strategy.platform.execution_allowed": "Execution allowed",

        "strategy.platform.family": "Family",
        "strategy.platform.name": "Название",
        "strategy.platform.version": "Версия",
        "strategy.platform.category": "Категория",
        "strategy.platform.status": "Статус",
        "strategy.platform.priority": "Приоритет",
        "strategy.platform.paper": "Paper",
        "strategy.platform.risk": "Risk",
        "strategy.platform.live": "Live",

        "strategy.platform.config_version": "Версия конфигурации",
        "strategy.platform.active": "Активна",
        "strategy.platform.config": "Параметры",

        "strategy.platform.feature": "Признак",
        "strategy.platform.required": "Обязательный",
        "strategy.platform.weight": "Вес",

        "strategy.platform.instrument": "Инструмент",
        "strategy.platform.timeframe": "TF",
        "strategy.platform.signal_ts": "Время сигнала",
        "strategy.platform.direction": "Направление",
        "strategy.platform.score": "Score",
        "strategy.platform.confidence": "Confidence",

        "common.yes": "Да",
        "common.no": "Нет",

        "status.ACTIVE": "Активно",
        "status.DISABLED": "Отключено",
        "status.READY": "Готово",
        "status.UNKNOWN": "Неизвестно",

        "health.HEALTHY": "Здорово",
        "health.DEGRADED": "Требует внимания",
        "health.FAILED": "Ошибка",

        "signal.LONG": "Long",
        "signal.SHORT": "Short",
        "signal.FLAT": "Нет сигнала",
    })
except NameError:
    pass
