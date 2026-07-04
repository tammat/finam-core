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

try:
    ROUTE_LABELS_RU.update({
        "/strategy-governance": "Governance стратегий",

        "strategy.governance.title": "Governance стратегий",
        "strategy.governance.subtitle": "Проверка целостности, готовности и допуска Strategy Platform.",
        "strategy.governance.overall": "Итог",
        "strategy.governance.score": "Governance Score",
        "strategy.governance.readiness": "Готовность",
        "strategy.governance.integrity": "Целостность",
        "strategy.governance.recommendation": "Рекомендация",

        "strategy.governance.registry": "Registry",
        "strategy.governance.configuration": "Configuration",
        "strategy.governance.dependency": "Dependencies",
        "strategy.governance.builder": "Builder",
        "strategy.governance.signal_store": "Signal Store",
        "strategy.governance.api": "API",
        "strategy.governance.ui": "UI",

        "governance.NOT_READY": "Не готово",
        "governance.READY_FOR_RESEARCH": "Готово к Research",
        "governance.READY_FOR_REPLAY": "Готово к Replay",
        "governance.READY_FOR_PAPER": "Готово к Paper",
        "governance.READY_FOR_SHADOW": "Готово к Shadow",
        "governance.READY_FOR_MICRO_LIVE": "Готово к Micro Live",
        "governance.READY_FOR_LIVE": "Готово к Live",

        "status.OK": "OK",
        "status.FAILED": "Ошибка",
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "/strategy-governance": "Governance стратегий",

        "strategy.governance.title": "Governance стратегий",
        "strategy.governance.subtitle": "Проверка целостности, готовности и допуска Strategy Platform.",
        "strategy.governance.overall": "Итог",
        "strategy.governance.score": "Governance Score",
        "strategy.governance.readiness": "Готовность",
        "strategy.governance.integrity": "Целостность",
        "strategy.governance.recommendation": "Рекомендация",

        "strategy.governance.registry": "Registry",
        "strategy.governance.configuration": "Configuration",
        "strategy.governance.dependency": "Dependencies",
        "strategy.governance.builder": "Builder",
        "strategy.governance.signal_store": "Signal Store",
        "strategy.governance.api": "API",
        "strategy.governance.ui": "UI",

        "governance.NOT_READY": "Не готово",
        "governance.READY_FOR_RESEARCH": "Готово к Research",
        "governance.READY_FOR_REPLAY": "Готово к Replay",
        "governance.READY_FOR_PAPER": "Готово к Paper",
        "governance.READY_FOR_SHADOW": "Готово к Shadow",
        "governance.READY_FOR_MICRO_LIVE": "Готово к Micro Live",
        "governance.READY_FOR_LIVE": "Готово к Live",

        "status.OK": "OK",
        "status.FAILED": "Ошибка",
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "/edge-platform": "Edge Platform",
        "edge.platform.title": "Edge Platform",
        "edge.platform.subtitle": "Оценка качества сигналов Strategy Platform через Platform API.",
        "edge.platform.summary": "Сводка",
        "edge.platform.decisions": "Решения",
        "edge.platform.configuration": "Конфигурация",
        "edge.platform.governance": "Governance",
        "edge.platform.edge_rows": "Всего решений",
        "edge.platform.allow_rows": "ALLOW",
        "edge.platform.observe_rows": "OBSERVE",
        "edge.platform.block_rows": "BLOCK",
        "edge.platform.ready_for_paper": "Ready for Paper",
        "edge.platform.unsafe_live": "Unsafe Live",
        "edge.platform.avg_edge_score": "Средний Edge Score",
        "edge.platform.avg_validation_score": "Средний Validation Score",
        "edge.platform.instrument": "Инструмент",
        "edge.platform.strategy": "Стратегия",
        "edge.platform.timeframe": "TF",
        "edge.platform.signal_ts": "Время сигнала",
        "edge.platform.edge_score": "Edge Score",
        "edge.platform.validation_score": "Validation",
        "edge.platform.decision": "Decision",
        "edge.platform.recommendation": "Recommendation",
        "edge.platform.replay": "Replay",
        "edge.platform.paper": "Paper",
        "edge.platform.live": "Live",
        "edge.platform.edge_name": "Edge",
        "edge.platform.enabled": "Включено",
        "edge.platform.config": "Параметры",
        "edge.platform.readiness": "Готовность",
        "edge.platform.score_engine": "Score Engine",
        "edge.platform.validation": "Validation",
        "edge.platform.decision_engine": "Decision Engine",
        "edge.platform.api": "API",
        "edge.platform.ui": "UI",
        "common.yes": "Да",
        "common.no": "Нет",
        "status.ACTIVE": "Активно",
        "status.DISABLED": "Отключено",
        "health.HEALTHY": "Здорово",
        "health.DEGRADED": "Требует внимания",
        "health.FAILED": "Ошибка",
        "decision.ALLOW": "ALLOW",
        "decision.OBSERVE": "OBSERVE",
        "decision.BLOCK": "BLOCK",
        "recommendation.READY_FOR_RISK_REVIEW": "Готово к risk review",
        "recommendation.WAIT_VALIDATION": "Ожидание validation",
        "recommendation.WAIT_RESEARCH": "Ожидание research",
        "governance.NOT_READY": "Не готово",
        "governance.READY_FOR_RESEARCH": "Готово к Research"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "/risk-platform": "Risk Platform",
        "risk.platform.title": "Risk Platform",
        "risk.platform.subtitle": "Контроль допуска Edge-решений через Risk Rules и Platform API.",
        "risk.platform.summary": "Сводка",
        "risk.platform.decisions": "Risk-решения",
        "risk.platform.configuration": "Конфигурация",
        "risk.platform.governance": "Governance",

        "risk.platform.risk_rows": "Всего решений",
        "risk.platform.allow_rows": "RISK_ALLOW",
        "risk.platform.observe_rows": "RISK_OBSERVE",
        "risk.platform.block_rows": "RISK_BLOCK",
        "risk.platform.ready_for_paper": "Ready for Paper",
        "risk.platform.unsafe_live": "Unsafe Live",
        "risk.platform.avg_risk_score": "Средний Risk Score",
        "risk.platform.avg_position_risk_score": "Position Risk",
        "risk.platform.avg_exposure_risk_score": "Exposure Risk",

        "risk.platform.instrument": "Инструмент",
        "risk.platform.strategy": "Стратегия",
        "risk.platform.timeframe": "TF",
        "risk.platform.signal_ts": "Время сигнала",
        "risk.platform.edge_score": "Edge Score",
        "risk.platform.validation_score": "Validation",
        "risk.platform.risk_score": "Risk Score",
        "risk.platform.position_risk": "Position",
        "risk.platform.exposure_risk": "Exposure",
        "risk.platform.daily_loss_risk": "Daily Loss",
        "risk.platform.correlation_risk": "Correlation",
        "risk.platform.kill_switch": "Kill Switch",
        "risk.platform.decision": "Decision",
        "risk.platform.recommendation": "Recommendation",
        "risk.platform.paper": "Paper",
        "risk.platform.live": "Live",

        "risk.platform.risk_name": "Risk",
        "risk.platform.enabled": "Включено",
        "risk.platform.config": "Параметры",

        "risk.platform.rule_engine": "Rule Engine",
        "risk.platform.builder": "Builder",
        "risk.platform.decision_engine": "Decision",
        "risk.platform.api": "API",
        "risk.platform.ui": "UI",
        "risk.platform.readiness": "Готовность",

        "risk.RISK_ALLOW": "Risk Allow",
        "risk.RISK_OBSERVE": "Risk Observe",
        "risk.RISK_BLOCK": "Risk Block",

        "recommendation.READY_FOR_TRADING": "Готово к Trading",
        "recommendation.WAIT_RISK_REVIEW": "Ожидание risk review",
        "recommendation.BLOCK_RISK": "Risk блок",
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "recommendation.PROCEED_TO_TRADING_PLATFORM": "Перейти к Trading Platform",
        "recommendation.FIX_RISK_PLATFORM": "Исправить Risk Platform",
        "recommendation.BLOCK_PLATFORM": "Заблокировать платформу",
        "status.OK": "OK",
        "status.FAILED": "Ошибка"
    })
except NameError:
    pass
