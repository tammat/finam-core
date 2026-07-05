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

try:
    ROUTE_LABELS_RU.update({
        "/trading-platform": "Trading Platform",
        "trading.platform.title": "Trading Platform",
        "trading.platform.subtitle": "Order Intent слой без отправки заявок брокеру.",
        "trading.platform.summary": "Сводка",
        "trading.platform.intents": "Order Intents",
        "trading.platform.configuration": "Конфигурация",
        "trading.platform.governance": "Governance",

        "trading.platform.intent_rows": "Всего intent",
        "trading.platform.paper_allowed": "Paper allowed",
        "trading.platform.shadow_allowed": "Shadow allowed",
        "trading.platform.micro_live_allowed": "Micro Live allowed",
        "trading.platform.live_allowed": "Live allowed",
        "trading.platform.order_sent": "Order sent",
        "trading.platform.paper_ready": "Paper ready",
        "trading.platform.block_rows": "Blocked",

        "trading.platform.instrument": "Инструмент",
        "trading.platform.strategy": "Стратегия",
        "trading.platform.timeframe": "TF",
        "trading.platform.signal_ts": "Время сигнала",
        "trading.platform.risk_score": "Risk Score",
        "trading.platform.side": "Side",
        "trading.platform.order_type": "Order Type",
        "trading.platform.quantity": "Quantity",
        "trading.platform.decision": "Decision",
        "trading.platform.recommendation": "Recommendation",
        "trading.platform.paper": "Paper",
        "trading.platform.live": "Live",
        "trading.platform.sent": "Sent",

        "trading.platform.trading_name": "Trading",
        "trading.platform.enabled": "Включено",
        "trading.platform.config": "Параметры",

        "trading.platform.builder": "Builder",
        "trading.platform.order_intent": "Order Intent",
        "trading.platform.api": "API",
        "trading.platform.ui": "UI",
        "trading.platform.readiness": "Готовность",

        "trading.PAPER_INTENT_READY": "Paper intent ready",
        "trading.TRADING_BLOCK": "Trading block",

        "recommendation.READY_FOR_PAPER_EXECUTION": "Готово к paper execution",
        "recommendation.WAIT_TRADING_REVIEW": "Ожидание trading review",
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "/portfolio-platform": "Portfolio Platform",
        "portfolio.platform.title": "Portfolio Platform",
        "portfolio.platform.subtitle": "Итоговое состояние портфеля, equity, позиции и exposure через Platform API.",
        "portfolio.platform.summary": "Сводка",
        "portfolio.platform.positions": "Позиции",
        "portfolio.platform.equity": "Equity",
        "portfolio.platform.configuration": "Конфигурация",
        "portfolio.platform.governance": "Governance",
        "portfolio.platform.cash": "Cash",
        "portfolio.platform.positions_value": "Positions Value",
        "portfolio.platform.equity_value": "Equity",
        "portfolio.platform.total_pnl": "Total PnL",
        "portfolio.platform.gross_exposure": "Gross Exposure",
        "portfolio.platform.net_exposure": "Net Exposure",
        "portfolio.platform.position_rows": "Всего позиций",
        "portfolio.platform.open_position_rows": "Открытые позиции",
        "portfolio.platform.instrument": "Инструмент",
        "portfolio.platform.asset_class": "Asset Class",
        "portfolio.platform.quantity": "Quantity",
        "portfolio.platform.avg_price": "Avg Price",
        "portfolio.platform.last_price": "Last Price",
        "portfolio.platform.market_value": "Market Value",
        "portfolio.platform.unrealized_pnl": "Unrealized PnL",
        "portfolio.platform.realized_pnl": "Realized PnL",
        "portfolio.platform.exposure": "Exposure",
        "portfolio.platform.status": "Статус",
        "portfolio.platform.portfolio_name": "Portfolio",
        "portfolio.platform.enabled": "Включено",
        "portfolio.platform.config": "Параметры",
        "portfolio.platform.builder": "Builder",
        "portfolio.platform.position_status": "Positions",
        "portfolio.platform.equity_status": "Equity",
        "portfolio.platform.api": "API",
        "portfolio.platform.ui": "UI",
        "portfolio.platform.readiness": "Готовность",
        "status.OPEN": "Открыта",
        "status.EMPTY": "Пусто"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "recommendation.PROCEED_TO_CONSOLIDATION": "Перейти к консолидации",
        "recommendation.FIX_PORTFOLIO_PLATFORM": "Исправить Portfolio Platform"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "research.queue.title": "Research Queue",
        "research.queue.subtitle": "Очередь исследовательских прогонов Strategy × Symbol × Timeframe × Parameters.",
        "research.queue.total": "Всего задач",
        "research.queue.queued": "В очереди",
        "research.queue.running": "В работе",
        "research.queue.done": "Завершено",
        "research.queue.failed": "Ошибки",
        "research.status.QUEUED": "В очереди",
        "research.status.RUNNING": "В работе",
        "research.status.DONE": "Завершено",
        "research.status.FAILED": "Ошибка",
        "research.status.CANCELLED": "Отменено"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.lab.title": "Edge Lab",
        "edge.lab.subtitle": "Лаборатория оценки исследовательских наблюдений и кандидатов edge.",
        "edge.lab.run": "Запуск исследования",
        "edge.lab.runs": "Запуски исследований",
        "edge.lab.observation": "Наблюдение",
        "edge.lab.observations": "Наблюдения",
        "edge.lab.candidate": "Edge-кандидат",
        "edge.lab.candidates": "Edge-кандидаты",
        "edge.lab.score": "Edge Score",
        "edge.lab.raw_score": "Raw Edge Score",
        "edge.lab.normalized_score": "Normalized Edge Score",
        "edge.lab.confidence": "Confidence",
        "edge.lab.stability": "Stability",
        "edge.lab.status": "Статус",
        "edge.lab.verdict": "Вердикт",
        "edge.lab.research_cost": "Research Cost",
        "edge.lab.batch": "Research Batch",
        "edge.lab.parameter_hash": "Parameter Hash",
        "edge.lab.dataset_version": "Dataset Version",
        "edge.lab.runner_version": "Runner Version",
        "edge.lab.score_formula_version": "Score Formula",
        "edge.status.QUEUED": "В очереди",
        "edge.status.RUNNING": "В работе",
        "edge.status.DONE": "Завершено",
        "edge.status.FAILED": "Ошибка",
        "edge.verdict.OBSERVED": "Наблюдение",
        "edge.verdict.REJECT": "Отклонить",
        "edge.verdict.CANDIDATE": "Кандидат",
        "edge.candidate.status.EDGE_CANDIDATE": "Edge-кандидат",
        "edge.candidate.status.VALIDATION": "Валидация",
        "edge.candidate.status.PAPER": "Paper",
        "edge.candidate.status.SHADOW": "Shadow",
        "edge.candidate.status.MICRO_LIVE": "Micro Live",
        "edge.validation.stage.NOT_STARTED": "Не начато",
        "edge.validation.stage.IN_PROGRESS": "В работе",
        "edge.validation.stage.PASSED": "Пройдено",
        "edge.validation.stage.FAILED": "Не пройдено"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.runner.title": "Edge Lab Runner",
        "edge.runner.subtitle": "Исполнитель очереди исследований без принятия торговых решений.",
        "edge.runner.running": "Выполняется",
        "edge.runner.done": "Завершено",
        "edge.runner.failed": "Ошибка",
        "edge.runner.retry": "Повтор",
        "edge.verdict.NO_TRADES": "Нет сделок"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.runner.title": "Edge Lab Runner",
        "edge.runner.subtitle": "Исполнитель очереди исследований без принятия торговых решений.",
        "edge.runner.running": "Выполняется",
        "edge.runner.done": "Завершено",
        "edge.runner.failed": "Ошибка",
        "edge.runner.retry": "Повтор",
        "edge.verdict.NO_TRADES": "Нет сделок"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "strategy.execution.runner.title": "Strategy Execution Runner",
        "strategy.execution.runner.subtitle": "Прогон исследовательских стратегий по историческим данным с записью trade set.",
        "edge.verdict.NO_MARKET_DATA": "Нет рыночных данных"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.score.engine.title": "Edge Score Engine",
        "edge.score.engine.subtitle": "Оценка исследовательских наблюдений без принятия решений о кандидатах.",
        "edge.score.raw": "Raw Score",
        "edge.score.normalized": "Normalized Score",
        "edge.score.confidence": "Confidence",
        "edge.score.stability": "Stability",
        "edge.score.research_cost": "Research Cost"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.discovery.engine.title": "Edge Discovery Engine",
        "edge.discovery.engine.subtitle": "Конфигурируемый движок отбора edge без жёстко заданных порогов в коде.",
        "edge.discovery.method": "Метод Discovery",
        "edge.discovery.rule": "Правило Discovery",
        "edge.discovery.rules": "Правила Discovery",
        "edge.discovery.operator": "Оператор",
        "edge.discovery.threshold": "Порог",
        "edge.discovery.weight": "Вес",
        "edge.discovery.family.RULE_ENGINE": "Rule Engine",
        "edge.discovery.family.MULTI_OBJECTIVE": "Multi-objective",
        "edge.discovery.family.PARAMETER_SEARCH": "Parameter Search",
        "edge.discovery.family.OPTIMIZATION": "Optimization"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.discovery.rule_rank.title": "Rule Rank Discovery",
        "edge.discovery.rule_rank.subtitle": "Метод ранжирования наблюдений через настраиваемые правила без хардкода порогов в коде.",
        "edge.discovery.rule_rank.method": "Метод Rule Rank",
        "edge.discovery.rule_rank.scanned": "Просканировано наблюдений",
        "edge.discovery.rule_rank.eligible": "Прошли ранжирование",
        "edge.discovery.rule_rank.created": "Создано кандидатов"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "strategy.dispatcher.title": "Strategy Dispatcher",
        "strategy.dispatcher.subtitle": "Маршрутизация стратегии к движку исполнения через registry без хардкода.",
        "strategy.dispatcher.engine": "Движок стратегии",
        "strategy.dispatcher.engine_version": "Версия движка",
        "strategy.dispatcher.engine_family": "Семейство движка",
        "strategy.dispatcher.unassigned": "Движок не назначен"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "strategy.dispatcher.title": "Strategy Dispatcher",
        "strategy.dispatcher.subtitle": "Маршрутизация стратегии к движку исполнения через registry без хардкода.",
        "strategy.dispatcher.engine": "Движок стратегии",
        "strategy.dispatcher.engine_version": "Версия движка",
        "strategy.dispatcher.engine_family": "Семейство движка",
        "strategy.dispatcher.unassigned": "Движок не назначен"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "strategy.dispatcher.title": "Strategy Dispatcher",
        "strategy.dispatcher.subtitle": "Маршрутизация стратегии к движку исполнения через registry без хардкода.",
        "strategy.dispatcher.engine": "Движок стратегии",
        "strategy.dispatcher.engine_version": "Версия движка",
        "strategy.dispatcher.engine_family": "Семейство движка",
        "strategy.dispatcher.unassigned": "Движок не назначен"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "strategy.engine.volatility_breakout.title": "Volatility Breakout Engine",
        "strategy.engine.volatility_breakout.subtitle": "Движок пробоя волатильности для исследовательского контура.",
        "strategy.engine.volatility_breakout.lookback": "Период окна",
        "strategy.engine.volatility_breakout.threshold": "Порог пробоя"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "trade.generator.title": "Trade Generator",
        "trade.generator.subtitle": "Компонент преобразования сигналов стратегии в исследовательские сделки.",
        "trade.generator.execution_model": "Модель исполнения",
        "trade.generator.version": "Версия генератора",
        "trade.generator.name": "Название генератора"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.sprint.title": "Edge Sprint",
        "edge.sprint.subtitle": "Короткий исследовательский цикл поиска edge-кандидатов.",
        "edge.sprint.code": "Код спринта",
        "edge.sprint.observations": "Наблюдения",
        "edge.sprint.with_trades": "Наблюдения со сделками",
        "edge.sprint.candidates": "Кандидаты",
        "edge.sprint.best_score": "Лучший Score",
        "edge.sprint.best_profit_factor": "Лучший Profit Factor",
        "edge.sprint.best_expectancy": "Лучшая Expectancy"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.lab.title": "Edge Lab",
        "edge.lab.subtitle": "Лаборатория оценки исследовательских наблюдений и кандидатов edge.",
        "edge.lab.run": "Запуск исследования",
        "edge.lab.runs": "Запуски исследований",
        "edge.lab.observation": "Наблюдение",
        "edge.lab.observations": "Наблюдения",
        "edge.lab.candidate": "Edge-кандидат",
        "edge.lab.candidates": "Edge-кандидаты",
        "edge.lab.score": "Edge Score",
        "edge.lab.raw_score": "Raw Edge Score",
        "edge.lab.normalized_score": "Normalized Edge Score",
        "edge.lab.confidence": "Confidence",
        "edge.lab.stability": "Stability",
        "edge.lab.status": "Статус",
        "edge.lab.verdict": "Вердикт",
        "edge.lab.research_cost": "Research Cost",
        "edge.lab.batch": "Research Batch",
        "edge.lab.parameter_hash": "Parameter Hash",
        "edge.lab.dataset_version": "Dataset Version",
        "edge.lab.runner_version": "Runner Version",
        "edge.lab.score_formula_version": "Score Formula",
        "edge.status.QUEUED": "В очереди",
        "edge.status.RUNNING": "В работе",
        "edge.status.DONE": "Завершено",
        "edge.status.FAILED": "Ошибка",
        "edge.verdict.OBSERVED": "Наблюдение",
        "edge.verdict.REJECT": "Отклонить",
        "edge.verdict.CANDIDATE": "Кандидат",
        "edge.candidate.status.EDGE_CANDIDATE": "Edge-кандидат",
        "edge.candidate.status.VALIDATION": "Валидация",
        "edge.candidate.status.PAPER": "Paper",
        "edge.candidate.status.SHADOW": "Shadow",
        "edge.candidate.status.MICRO_LIVE": "Micro Live",
        "edge.validation.stage.NOT_STARTED": "Не начато",
        "edge.validation.stage.IN_PROGRESS": "В работе",
        "edge.validation.stage.PASSED": "Пройдено",
        "edge.validation.stage.FAILED": "Не пройдено"
    })
except NameError:
    pass

try:
    ROUTE_LABELS_RU.update({
        "edge.audit.title": "Edge Audit",
        "edge.audit.subtitle": "Диагностика воронки EDGE Factory",
        "edge.audit.report": "Отчёт аудита"
    })
except NameError:
    pass
