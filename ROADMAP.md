FINAM_CORE

ROADMAP

ТЕКУЩИЙ СТАТУС

Architecture Freeze V3

Архитектура проекта зафиксирована.

Все дальнейшие изменения выполняются только внутри утвержденной архитектуры.

=========================================================
ОБЩАЯ АРХИТЕКТУРА
=========================================================

Market
    ↓
Feature Store
    ↓
Research
    ↓
Validation
    ↓
Risk
    ↓
Trading
    ↓
Execution
    ↓
Portfolio
    ↓
Runtime

=========================================================
ЗАВЕРШЕНО
=========================================================

DATA PLATFORM

✓ PostgreSQL
✓ Market Bars
✓ History
✓ Timers
✓ Monitoring
✓ Knowledge Graph API

MARKET PLATFORM

✓ Market Universe
✓ Market Ranking
✓ Research Queue

RESEARCH PLATFORM

✓ Edge Discovery
✓ Validation Queue
✓ Validation Pipeline
✓ Robustness
✓ OOS Validation
✓ OOS Backtest

PAPER PLATFORM

✓ Paper Runtime
✓ Sample Collection
✓ Timers
✓ Dashboards

UI PLATFORM

✓ Единый интерфейс
✓ Русификация
✓ Вложенное меню
✓ Dashboard
✓ Mobile UI
✓ API Only
✓ Systemd

ARCHITECTURE

✓ Architecture Freeze V3

=========================================================
ТЕКУЩАЯ ФАЗА
=========================================================

PHASE III

PLATFORM CORE

=========================================================
БЛИЖАЙШИЕ ЭТАПЫ
=========================================================

1

FEATURE_STORE_V1

Создание единого слоя признаков.

2

FEATURE_STORE_HISTORY_BACKFILL_V1

Расчет признаков для всей истории.

3

MULTI_STRATEGY_ENGINE_V1

Подключение нескольких исследовательских стратегий.

4

EDGE_DISCOVERY_ENGINE_V1

Автоматический поиск новых Edge.

5

EDGE_SCORECARD_V1

Единая оценка качества найденных преимуществ.

=========================================================
СЛЕДУЮЩАЯ ФАЗА
=========================================================

PHASE IV

RISK PLATFORM

RISK_ENGINE_FOUNDATION_V1

PORTFOLIO_RISK_ENGINE_V1

POSITION_SIZING_ENGINE_V1

CORRELATION_ENGINE_V1

EXPOSURE_ENGINE_V1

LIQUIDITY_ENGINE_V1

SPREAD_ENGINE_V1

SLIPPAGE_ENGINE_V1

REGIME_ENGINE_V1

STRATEGY_HEALTH_ENGINE_V1

KILL_SWITCH_ENGINE_V1

=========================================================
ПОСЛЕ РИСКОВ
=========================================================

PHASE V

TRADING PLATFORM

TRADING_ENGINE_V1

ORDER_ROUTER_V1

EXECUTION_POLICY_V1

DECISION_JOURNAL_V1

=========================================================
ПОСЛЕ ТОРГОВЛИ
=========================================================

PHASE VI

EXECUTION PLATFORM

PAPER_ENGINE_V2

MICRO_LIVE_ENGINE_V1

LIVE_ENGINE_V1

=========================================================
ПОСЛЕ ИСПОЛНЕНИЯ
=========================================================

PHASE VII

PORTFOLIO PLATFORM

PORTFOLIO_ENGINE_V1

CAPITAL_ENGINE_V1

PERFORMANCE_ENGINE_V1

STATISTICS_ENGINE_V1

=========================================================
ФИНАЛЬНАЯ ФАЗА
=========================================================

PHASE VIII

RUNTIME PLATFORM

RUNTIME_SUPERVISOR_V2

AUTOMATIC GOVERNANCE

SELF MONITORING

SELF RECOVERY

AUTOMATIC REPORTING

=========================================================
ОСНОВНЫЕ ПРАВИЛА
=========================================================

Feature Store является единственным источником признаков.

Research никогда не отправляет заявки.

Validation никогда не принимает торговых решений.

Risk является единственным источником оценки риска.

Trading является единственным источником торгового решения.

Execution является единственным источником исполнения заявок.

Portfolio является единственным источником состояния капитала.

Runtime управляет жизненным циклом системы.

=========================================================
КОНЕЧНАЯ ЦЕЛЬ
=========================================================

Создание полностью автономной исследовательской и торговой платформы, способной:

• самостоятельно анализировать рынок;

• автоматически находить статистические преимущества;

• подтверждать их устойчивость;

• оценивать риски;

• принимать торговые решения;

• безопасно исполнять сделки;

• контролировать капитал и портфель;

• самостоятельно контролировать собственное состояние.

Конец документа.
