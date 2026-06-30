# CANONICAL_FINANCIAL_DOMAIN_MODEL_V1

## Статус

FOUNDATION

## Назначение

CANONICAL_FINANCIAL_DOMAIN_MODEL_V1 является главным архитектурным документом MarketCore.

Любая новая сущность сначала появляется в этом документе, проходит архитектурную проверку и только после этого реализуется в коде, PostgreSQL, Registry, Knowledge Graph, AI, UI или Runtime.

## GOLDEN_RULE_V1

Любая новая сущность сначала появляется в CANONICAL_FINANCIAL_DOMAIN_MODEL_V1, и только потом реализуется в коде.

## Архитектурные принципы

1. Сначала предметная область, затем код.
2. Single Source of Truth для каждой сущности.
3. Event First: ключевые изменения фиксируются как события.
4. Knowledge Graph хранит связи, но не копирует данные.
5. AI не обращается к RAW-данным напрямую.
6. UI только читает данные.
7. Runtime и Execution не изменяются на этапе проектирования модели.
8. PostgreSQL является единственным хранилищем.
9. SQLite запрещён.
10. Новые сущности проходят Architecture Review до реализации.

## Платформенные домены

### 1. Financial Universe

- Universe
- Region
- Country
- Currency
- Venue
- Exchange
- Market
- Asset Class
- Asset
- Instrument
- Contract

### 2. Market Structure

- Trading Calendar
- Trading Session
- Auction
- Continuous Trading
- Clearing
- Settlement
- Corporate Action
- Holiday
- Expiration
- Rollover

### 3. Asset Classes

- EQUITY
- ETF
- BOND
- INDEX
- FUTURE
- OPTION
- FOREX_SPOT
- FOREX_FORWARD
- FOREX_SWAP
- FOREX_NDF
- COMMODITY_SPOT
- COMMODITY_FUTURE
- CRYPTO_SPOT
- CRYPTO_FUTURE
- CFD
- MONEY_MARKET

### 4. Forex Domain

- Currency
- Currency Pair
- Base Currency
- Quote Currency
- Settlement Currency
- Pip
- Tick
- Swap
- Rollover
- Funding Rate
- Triangular FX Route

### 5. Market Data

- Quote
- Order Book
- Trade Tick
- Bar
- Volume
- VWAP
- Open Interest
- Funding
- Volatility
- Volatility Surface
- Greeks
- Data Quality Event

### 6. Trading Domain

- Signal
- Risk Decision
- Order
- Execution Report
- Fill
- Position
- Trade
- Portfolio
- Cash Flow
- PnL

### 7. Order Types

- MARKET
- LIMIT
- STOP
- STOP_LIMIT
- ICEBERG
- TWAP
- VWAP
- PEGGED
- SYNTHETIC

### 8. Position Types

- LONG
- SHORT
- FLAT
- HEDGED
- SYNTHETIC
- SPREAD
- BASKET

### 9. Strategy Domain

- Strategy Family
- Strategy
- Trading Idea
- Execution Style
- Entry Rule
- Exit Rule
- Risk Profile
- Portfolio Construction Rule

### 10. Strategy Families

- TREND_FOLLOWING
- MEAN_REVERSION
- MOMENTUM
- BREAKOUT
- SCALPING
- SWING
- STATISTICAL_ARBITRAGE
- CROSS_ASSET_ARBITRAGE
- INTER_EXCHANGE_ARBITRAGE
- CALENDAR_SPREAD
- PAIRS_TRADING
- VOLATILITY_TRADING
- MARKET_MAKING
- LIQUIDITY_CAPTURE
- EXECUTION_ONLY

### 11. Trading Idea Types

- DIRECTIONAL
- RELATIVE_VALUE
- SPREAD
- CARRY
- HEDGE
- ARBITRAGE
- VOLATILITY
- EVENT_DRIVEN
- LIQUIDITY
- EXECUTION

### 12. Arbitrage Types

- SPATIAL_ARBITRAGE
- TEMPORAL_ARBITRAGE
- CROSS_EXCHANGE
- CROSS_BROKER
- CROSS_ASSET
- STATISTICAL_ARBITRAGE
- TRIANGULAR_FOREX_ARBITRAGE
- FUNDING_ARBITRAGE
- BASIS_ARBITRAGE
- CALENDAR_ARBITRAGE

### 13. Research Domain

- Dataset
- Feature
- Label
- Model
- Experiment
- Candidate
- Benchmark
- Validation
- Walk Forward
- Out Of Sample
- Report

### 14. Dataset Types

- MARKET_DATASET
- TRADE_DATASET
- FEATURE_DATASET
- LABEL_DATASET
- TRAINING_DATASET
- VALIDATION_DATASET
- TEST_DATASET
- OUT_OF_SAMPLE_DATASET

### 15. Knowledge Domain

- Registry
- Relationship
- Knowledge Graph
- Ontology
- Graph Path
- Graph Statistics

### 16. AI Domain

- AI Agent
- AI Capability
- AI Policy
- AI Prompt
- AI Workflow
- AI Evaluation
- AI Recommendation
- AI Decision Trace

### 17. AI Roles

- DATA_AGENT
- RESEARCH_AGENT
- RISK_AGENT
- EXECUTION_AGENT
- PORTFOLIO_AGENT
- EXPLAINABILITY_AGENT
- OPTIMIZATION_AGENT
- MONITORING_AGENT

### 18. Governance Domain

- Audit Event
- Version
- Lineage
- Provenance
- Data Quality
- Normalization Version
- Feature Pipeline Version
- Model Version
- Experiment Version

## Каноническая цепочка прослеживаемости

Market Bar
→ Signal
→ Risk Decision
→ Order
→ Execution Report
→ Fill
→ Position
→ Trade
→ PnL
→ Dataset
→ Feature
→ Model
→ Experiment
→ Candidate
→ Knowledge Graph
→ AI Recommendation

## Правила идентификаторов

Канонические идентификаторы:

- universe_id
- venue_id
- exchange_id
- market_id
- asset_class_id
- asset_id
- instrument_id
- contract_id
- session_id
- timeframe_id
- bar_id
- signal_id
- risk_event_id
- order_id
- execution_report_id
- fill_id
- position_id
- trade_id
- pnl_id
- dataset_id
- feature_id
- model_id
- experiment_id
- candidate_id
- ai_component_id

Символ, тикер, код брокера и код биржи являются атрибутами, а не первичными идентификаторами.

## Правила времени

Ключевые поля времени:

- event_time
- source_time
- received_at
- normalized_at
- created_at
- updated_at
- effective_from
- effective_to

## Normalization Policy

1. RAW-данные не используются напрямую Research, AI или UI.
2. Research использует только нормализованные сущности.
3. AI использует только Registry, Knowledge Graph, Normalized Market, Normalized Trade и Research Dataset.
4. Knowledge Graph не хранит миллионы технических баров.
5. Любая нормализованная запись должна иметь provenance.
6. Любая сделка должна быть прослеживаема до рыночного события или явно маркироваться как ручная/внешняя.

## Запреты

- Запрещено добавлять новую сущность сразу в код без описания здесь.
- Запрещено создавать второй источник истины.
- Запрещено смешивать Market Domain и Trading Domain в одной сущности.
- Запрещено смешивать Registry и Knowledge Graph.
- Запрещено хранить рыночные знания в AI Registry.
- Запрещено использовать SQLite.
- Запрещено включать execution side effects на этапе design.

## План реализации

1. CANONICAL_FINANCIAL_DOMAIN_MODEL_V1
2. MARKET_DATA_NORMALIZATION_DESIGN_V1
3. MARKET_DATA_NORMALIZATION_SCHEMA_V1
4. MARKET_DATA_NORMALIZATION_BUILDER_V1
5. MARKET_DATA_NORMALIZATION_VALIDATION_V1
6. MARKET_DATA_NORMALIZATION_CLI_V1
7. MARKET_DATA_NORMALIZATION_UI_V1
8. MARKET_DATA_NORMALIZATION_COMPLETE_V1
