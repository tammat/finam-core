# MARKETCORE / FINAM_CORE — PROJECT STATE

Версия состояния: V1
Статус документа: SOURCE_OF_OPERATIONAL_CONTEXT
Дата актуализации: требуется заполнить
Ответственный: команда MarketCore

---

## 1. ЦЕЛЬ ПРОЕКТА

Создание production-grade, event-driven, multi-asset торговой и исследовательской системы для рынка MOEX и брокера Finam.

Основная экономическая цель:

- обнаружение статистически подтвержденного edge;
- проверка его устойчивости;
- безопасное исполнение;
- получение прибыли после комиссий, проскальзывания и прочих торговых издержек.

---

## 2. ЗАФИКСИРОВАННАЯ АРХИТЕКТУРА

Архитектура заблокирована:

- core/
- execution/
- portfolio/
- risk/
- strategy/
- data/
- storage/
- tests/
- main.py

Обязательные архитектурные правила:

1. Event-driven engine.
2. Strategy изолирована от execution.
3. Централизованный Risk Engine.
4. Portfolio агрегирует все позиции.
5. PostgreSQL — единственная основная база данных.
6. SQLite запрещен.
7. AI-слой не имеет права отправлять ордера напрямую.
8. Все сигналы, включая отклоненные, журналируются.
9. Все сделки, risk events, features и решения журналируются.
10. Стабильные потоки нельзя переписывать агрессивно.
11. Изменения выполняются минимальными, проверяемыми шагами.
12. Реальная торговля не включается без отдельного подтвержденного допуска.

---

## 3. RISK ENGINE — ОБЯЗАТЕЛЬНЫЕ ОГРАНИЧЕНИЯ

Централизованный Risk Engine должен контролировать:

- max_risk_per_trade;
- daily_loss_limit;
- exposure_limit;
- kill_switch;
- correlation_filter;
- лимиты по инструменту;
- лимиты по классу активов;
- лимиты по портфелю;
- повторную отправку ордеров;
- stale market data;
- отсутствие или неполноту комиссий;
- расхождения между broker state и internal state.

Risk Engine имеет право отклонить любой сигнал.

Strategy не может обходить Risk Engine.

Execution не может исполнять заявку без положительного решения Risk Engine.

---

## 4. ТЕКУЩИЙ РЕЖИМ

Текущий основной режим:

RESEARCH / SHADOW

По умолчанию:

- real_trading_enabled=0
- execution_enabled=0
- micro_live_allowed=0
- ai_direct_orders_allowed=0

Изменение этих значений допускается только отдельным решением после прохождения всех контрольных ворот.

---

## 5. ТЕКУЩЕЕ СОСТОЯНИЕ ИССЛЕДОВАНИЙ

Система развивается уже не только как торговый робот, но и как исследовательская платформа.

Реализованные или ранее зафиксированные направления:

- сбор реальных рыночных данных;
- PostgreSQL research schemas;
- multi-asset research universe;
- signal flow;
- trade attribution;
- risk context;
- regime analysis;
- shadow runtime;
- MTM/equity monitoring;
- edge discovery;
- edge scoring;
- session profiling;
- data source registry;
- synthetic/generated data registry;
- broker/exchange/instrument ontology;
- комиссия и execution costs как обязательная часть оценки edge.

Требуется подтверждение фактического состояния каждого компонента по коду, миграциям, таблицам и Bash-тестам.

---

## 6. ИЗВЕСТНЫЕ EDGE-КАНДИДАТЫ

Ранее зафиксированный исследовательский кандидат:

- Instrument: BRM6@RTSX
- Strategy: BR_CONSERVATIVE_BREAKOUT
- Timeframe: M5
- Trades: 77
- Wins: 36
- Losses: 41
- WinRate: 46.75%
- NetPnL: 147.290019
- Expectancy: 1.912857
- ProfitFactor: 1.942233
- Status: RESEARCH_CANDIDATE
- Micro Live: NOT ALLOWED

Эти показатели нельзя считать подтвержденным edge без проверки:

- полноты комиссий;
- проскальзывания;
- качества исходных данных;
- look-ahead bias;
- survivorship bias;
- переобучения;
- out-of-sample;
- walk-forward;
- устойчивости по режимам рынка;
- устойчивости по контрактам;
- достаточности выборки;
- воспроизводимости результата.

Упоминались также три edge-кандидата по LKOH.

Их параметры должны быть восстановлены из PostgreSQL и исследовательских артефактов. До восстановления они не считаются подтвержденными.

---

## 7. ЗАФИКСИРОВАННЫЙ ПОРЯДОК ВАЛИДАЦИИ EDGE

Для каждого edge-кандидата:

1. Forensic audit.
2. Проверка data lineage.
3. Проверка комиссий и торговых издержек.
4. Проверка количества и качества сделок.
5. Robustness tests.
6. Parameter sensitivity.
7. Regime decomposition.
8. Out-of-sample validation.
9. Walk-forward validation.
10. Shadow forward test.
11. Risk-adjusted evaluation.
12. Micro-live admission review.
13. Только после допуска — ограниченный micro-live.

Нельзя переходить к реальной торговле только на основании backtest PnL или Profit Factor.

---

## 8. МОДЕЛЬ РЫНКА

Модель рынка должна предшествовать выбору и применению стратегии.

Минимальные измерения модели рынка:

- trend / range;
- volatility regime;
- liquidity;
- spread;
- volume;
- session;
- time-of-day;
- contract lifecycle;
- expiration proximity;
- gaps;
- news/event risk;
- correlation regime;
- execution quality;
- transaction costs.

Стратегия должна оцениваться только в тех режимах, для которых она предназначена.

---

## 9. КОМИССИИ И ТОРГОВЫЕ ИЗДЕРЖКИ

Запрещено принимать решение об edge без учета:

- брокерской комиссии;
- биржевой комиссии;
- клиринговых сборов;
- проскальзывания;
- bid/ask spread;
- частичного исполнения;
- стоимости переноса позиции;
- вариационной маржи;
- стоимости фондирования, если применимо;
- налоговых и иных внешних издержек — отдельно от trading PnL.

Должны храниться как минимум:

- gross_pnl;
- commission;
- exchange_fee;
- clearing_fee;
- slippage;
- spread_cost;
- financing_cost;
- net_pnl.

---

## 10. ИСТОЧНИКИ ДАННЫХ

Все источники должны быть зарегистрированы.

Категории:

- broker API;
- exchange data;
- imported historical data;
- generated/synthetic data;
- derived features;
- corrected/backfilled data.

Для каждого набора данных требуется:

- source;
- symbol;
- timeframe;
- first timestamp;
- last timestamp;
- ingestion timestamp;
- timezone;
- completeness;
- duplicates;
- gaps;
- correction status;
- synthetic flag;
- schema version.

Сгенерированные данные нельзя смешивать с реальными без явного признака происхождения.

---

## 11. ПРОИЗВОДСТВЕННЫЕ ЗАПРЕТЫ

Запрещено:

- включать real execution неявно;
- отправлять ордера из AI-слоя;
- обходить Risk Engine;
- использовать SQLite;
- скрывать rejected signals;
- считать gross PnL чистой прибылью;
- использовать неподтвержденные данные;
- менять стабильные потоки без regression test;
- хардкодить веса моделей без конфигурации и версионирования;
- считать исследовательского кандидата готовой стратегией;
- включать micro-live без формального допуска;
- переписывать архитектуру после Architecture Lock.

---

## 12. ОБЯЗАТЕЛЬНАЯ НАБЛЮДАЕМОСТЬ

Необходимо журналировать:

- market events;
- generated features;
- strategy signals;
- rejected signals;
- risk decisions;
- order intents;
- orders;
- broker acknowledgements;
- partial fills;
- fills;
- cancellations;
- positions;
- portfolio exposure;
- PnL;
- commissions;
- slippage;
- runtime errors;
- stale data;
- reconciliation discrepancies;
- configuration version;
- strategy version;
- model version;
- source-data version.

---

## 13. ТЕСТИРОВАНИЕ

Правило проекта:

- тесты запускаются через Bash;
- pytest не используется;
- unittest не используется;
- каждый тест возвращает корректный exit code;
- каждый этап должен иметь явный VERDICT;
- тесты не должны включать real trading;
- тесты не должны изменять production state без явного режима migrate/apply.

Формат успешного результата:

VERDICT=<COMPONENT>_READY
VERDICT=TEST_<COMPONENT>_OK

---

## 14. CHECKPOINT И GIT

Перед любым изменением необходимо определить:

- текущую ветку;
- текущий commit;
- незакоммиченные изменения;
- последний релевантный checkpoint/tag;
- возможность отката.

Запрещено автоматически коммитить неизвестные или посторонние изменения.

Текущие значения требуется заполнить командами Git:

- Branch: NOT_CAPTURED
- Commit: NOT_CAPTURED
- Last checkpoint: NOT_CAPTURED
- Working tree status: NOT_CAPTURED

---

## 15. ИЗВЕСТНЫЕ ПРОБЕЛЫ

Требуют обязательной фактической проверки:

1. Полнота учета комиссий во всех research pipelines.
2. Полнота модели рынка.
3. Data lineage для реальных и синтетических данных.
4. Наличие единой воронки принятия решений.
5. Reconciliation internal state с Finam.
6. Точная статистика трех edge-кандидатов по LKOH.
7. Актуальный статус BRM6@RTSX.
8. Достаточность выборок.
9. Корректность edge score без хардкода.
10. Shadow-forward результаты.
11. Portfolio-level risk.
12. Correlation filter.
13. Kill switch.
14. Daily loss limit.
15. Exposure limits.
16. Допуск к micro-live.
17. Актуальное состояние PostgreSQL migrations.
18. Состояние web control panel.
19. Состояние сервисов systemd.
20. Фактическая готовность к реальной торговле.

---

## 16. ТЕКУЩИЙ УПРАВЛЕНЧЕСКИЙ ВЫВОД

Система имеет значительный исследовательский и инфраструктурный контур.

Однако наличие исследовательских кандидатов не означает готовность к реальной торговле.

До подтверждения:

- комиссий;
- market model;
- data quality;
- robustness;
- out-of-sample;
- shadow-forward;
- reconciliation;
- portfolio risk;
- operational safety;

статус должен оставаться:

RESEARCH / SHADOW / REAL EXECUTION DISABLED

---

## 17. СЛЕДУЮЩИЙ ЭТАП

Следующий этап:

PROJECT_STATE_FACTUAL_RECONCILIATION_V1

Цель:

1. Снять фактическое состояние Git.
2. Инвентаризировать PostgreSQL schemas и tables.
3. Инвентаризировать systemd services.
4. Найти последние успешные VERDICT.
5. Восстановить edge-кандидатов.
6. Проверить учет комиссий.
7. Сопоставить данный документ с фактическим кодом.
8. Заменить NOT_CAPTURED и неподтвержденные сведения проверенными данными.

До завершения reconciliation:

- architecture_changed=0
- runtime_changed=0
- execution_changed=0
- real_trading_enabled=0
- micro_live_allowed=0

---

## 18. ПРАВИЛО ОБНОВЛЕНИЯ ДОКУМЕНТА

После каждого завершенного этапа обновляются:

- дата;
- текущий статус;
- последний commit;
- checkpoint/tag;
- завершенные работы;
- подтвержденные результаты;
- известные риски;
- следующий конкретный этап.

Чат не является единственным источником истины.

Источник истины:

1. Git.
2. Код.
3. PostgreSQL.
4. Миграции.
5. Bash-тесты.
6. Логи.
7. PROJECT_STATE.md как агрегированный контекст.
