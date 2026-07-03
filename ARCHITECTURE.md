cat > ARCHITECTURE.md <<'EOF'
FINAM_CORE
ARCHITECTURE FREEZE V3

ОБЩИЕ ПРИНЦИПЫ

1. Архитектура является фиксированной.
2. Все новые компоненты должны соответствовать данной архитектуре.
3. Прямые зависимости между ядрами запрещены.
4. Взаимодействие выполняется только через утвержденные контракты.
5. Каждый модуль отвечает только за одну область ответственности.

АРХИТЕКТУРА

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

ЯДРА СИСТЕМЫ

1. MARKET CORE

Назначение:
Получение, хранение и сопровождение рыночных данных.

Включает:

- Market Bars
- Sessions
- Calendar
- Universe
- Corporate Actions
- Market Freshness

Не имеет права:

- вычислять признаки
- искать Edge
- принимать торговые решения

2. FEATURE STORE

Назначение:
Единое централизованное хранилище признаков.

Включает:

- Price
- Trend
- Momentum
- Volatility
- Breakout
- Volume
- Session
- Quality

Все признаки рассчитываются только здесь.

Запрещено повторно вычислять:

- ATR
- EMA
- RSI
- Donchian
- Bollinger
- Volume Ratio
- Returns
- Volatility
- Session Features

Все остальные ядра читают только Feature Store.

3. RESEARCH PLATFORM

Назначение:
Поиск статистических преимуществ.

Включает:

- Market Ranking
- Research Queue
- Edge Discovery
- Validation
- Scorecards
- OOS

Не имеет права:

- управлять рисками
- отправлять заявки
- работать с брокером

4. RISK PLATFORM

Назначение:
Оценка возможности торговли.

Включает:

- Portfolio Risk
- Position Sizing
- Exposure
- Correlation
- Liquidity
- Spread
- Slippage
- Drawdown
- Regime
- Strategy Health
- Kill Switch

Результат работы:

PASS

WARN

BLOCK

Risk Engine не отправляет заявки.

5. TRADING PLATFORM

Назначение:
Принятие торгового решения.

Получает:

Risk Verdict

Возвращает:

Trade Decision

Включает:

- Trade Intent
- Trade Decision
- Order Routing
- Execution Policy

Не взаимодействует напрямую с брокером.

6. EXECUTION PLATFORM

Назначение:
Исполнение торговых решений.

Включает:

- Paper
- Micro Live
- Live

Получает только Order Intent.

7. PORTFOLIO PLATFORM

Назначение:
Учет состояния капитала.

Включает:

- Cash
- Positions
- Exposure
- Equity
- Performance
- Capital

Является единственным источником состояния портфеля.

8. RUNTIME PLATFORM

Назначение:
Управление жизненным циклом системы.

Включает:

- Supervisor
- Timers
- Services
- Monitoring
- Health Checks

КОНТРАКТЫ

StrategySignal

↓

FeatureSnapshot

↓

RiskContext

↓

RiskVerdict

↓

TradeIntent

↓

TradeDecision

↓

OrderIntent

↓

ExecutionReport

↓

PortfolioState

ЗАПРЕЩЕНО

Любой модуль не имеет права самостоятельно:

- читать Market Bars для вычисления индикаторов;
- вычислять ATR;
- вычислять EMA;
- вычислять RSI;
- вычислять Donchian;
- вычислять признаки, уже существующие в Feature Store;
- принимать торговое решение вместо Trading Engine;
- отправлять заявки брокеру;
- обходить Risk Engine;
- изменять Portfolio напрямую.

ПРАВИЛА ДОБАВЛЕНИЯ НОВОГО ФУНКЦИОНАЛА

Перед разработкой нового модуля необходимо определить, к какому ядру он относится:

- Market
- Feature Store
- Research
- Validation
- Risk
- Trading
- Execution
- Portfolio
- Runtime

Если модуль не относится ни к одному ядру, архитектура должна быть пересмотрена до начала разработки.

ПРИНЦИПЫ

Один модуль — одна ответственность.

Один источник данных — одна версия истины.

Feature Store — единственный источник признаков.

Portfolio — единственный источник состояния капитала.

Risk Engine — единственный источник оценки риска.

Trading Engine — единственный источник торгового решения.

Execution Engine — единственный источник исполнения заявок.

Архитектура изменяется только через официальное решение об изменении Architecture Freeze.

Конец документа.
EOF

echo "ARCHITECTURE.md created."
