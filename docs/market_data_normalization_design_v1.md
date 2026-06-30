# MARKET_DATA_NORMALIZATION_DESIGN_V1

## Статус

DESIGN

## Основание

Документ реализует первый прикладной слой после CANONICAL_FINANCIAL_DOMAIN_MODEL_V1.

GOLDEN_RULE_V1: любая новая сущность сначала появляется в CANONICAL_FINANCIAL_DOMAIN_MODEL_V1, и только потом реализуется в коде.

## Цель

Создать проект нормализованного слоя рыночных данных MarketCore.

Слой не меняет Runtime, Execution, Orders, Fills и Micro Live.

## Source of Truth

CANONICAL_FINANCIAL_DOMAIN_MODEL_V1 является источником предметной области.

Normalized Market Layer является источником истины для рыночных сущностей.

RAW-данные остаются источником загрузки, но не являются источником истины для Research, AI и UI.

## Домены нормализации V1

### Financial Universe

- venue
- exchange
- market
- asset_class
- asset
- instrument
- contract

### Market Structure

- trading_calendar
- trading_session
- timeframe
- expiration
- rollover

### Forex

- currency
- currency_pair
- base_currency
- quote_currency
- settlement_currency
- pip
- swap
- rollover
- triangular_fx_route

### Market Data

- quote
- trade_tick
- bar
- order_book_snapshot
- open_interest
- funding_rate
- volatility_observation

### Data Quality

- missing_data
- duplicate_data
- bad_tick
- stale_bar
- session_gap
- source_gap
- normalization_error

## Канонические сущности V1

### Instrument

Instrument описывает экономический инструмент независимо от конкретного брокерского символа.

Примеры:
- SBER equity
- Brent crude oil future family
- Natural gas future family
- USD/RUB forex pair

### Contract

Contract описывает конкретный торгуемый контракт или конкретную форму инструмента.

Примеры:
- BRU6
- NGU6
- SBER@MISX
- USD/RUB TOD
- USD/RUB TOM

### Symbol Alias

Symbol Alias связывает внешние коды с каноническими сущностями.

Примеры:
- BRM6@RTSX
- BR-7.26
- SBER@MISX
- SiU6
- USDRUB_TOM

### Bar

Bar является нормализованной OHLCV-записью.

Обязательная привязка:
- venue
- instrument
- contract, если применимо
- timeframe
- session
- source
- event_time

## Asset Classes V1

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

## Market Data Normalization Chain

RAW Source
→ Source Symbol
→ Symbol Alias
→ Instrument
→ Contract
→ Session
→ Timeframe
→ Normalized Bar
→ Data Quality Event
→ Research Dataset
→ Feature
→ Model
→ Experiment
→ Knowledge Graph
→ AI

## Правила идентификаторов

В нормализованном слое используются внутренние идентификаторы:

- venue_id
- exchange_id
- market_id
- asset_class_id
- asset_id
- instrument_id
- contract_id
- symbol_alias_id
- session_id
- timeframe_id
- bar_id
- data_quality_event_id

Символы брокера, тикеры и биржевые коды являются атрибутами, а не первичными идентификаторами.

## Правила времени

Каждая нормализованная рыночная запись должна поддерживать:

- event_time
- source_time
- received_at
- normalized_at
- created_at

Для контрактов и справочников дополнительно:

- effective_from
- effective_to

## Provenance

Каждая нормализованная запись должна отвечать на вопросы:

- источник данных
- внешний символ
- версия нормализации
- время получения
- время нормализации
- качество записи

## Data Quality Policy

Ошибочные или неполные данные не удаляются молча.

Они получают статус:

- VALID
- WARNING
- REJECTED
- REVIEW_REQUIRED

## Запреты

- Запрещено обращаться к RAW market data из Research напрямую.
- Запрещено использовать broker symbol как первичный ключ.
- Запрещено смешивать Instrument и Contract.
- Запрещено смешивать Market Data и Trade Data в одной сущности.
- Запрещено менять Runtime, Execution, Orders, Fills на этапе Design.
- Запрещено включать Micro Live.
- Запрещено использовать SQLite.

## Границы V1

В V1 проектируется только Market Data Normalization.

Не входит:
- нормализация сделок
- нормализация приказов
- нормализация портфеля
- AI Intelligence
- live execution

Эти слои идут после Market Data Normalization.

## План реализации

1. MARKET_DATA_NORMALIZATION_DESIGN_V1
2. MARKET_DATA_NORMALIZATION_SCHEMA_V1
3. MARKET_DATA_NORMALIZATION_BUILDER_V1
4. MARKET_DATA_NORMALIZATION_VALIDATION_V1
5. MARKET_DATA_NORMALIZATION_CLI_V1
6. MARKET_DATA_NORMALIZATION_UI_V1
7. MARKET_DATA_NORMALIZATION_COMPLETE_V1
