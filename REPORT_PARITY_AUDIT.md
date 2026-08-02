# Research → Runtime parity audit

Дата и время среза: 2026-08-02 17:10 MSK  
Репозиторий: `/opt/finam-core`  
Ветка: `codex/research-edge-v5`  
Проверяемый HEAD: `64c119f4420396235a637faa50171324fa8691fb`  
Рабочая директория: только `?? REPORT_PARITY_AUDIT.md`; иных незакоммиченных изменений не обнаружено.  
Режим: read-only; исходный код, БД и сервисы не изменялись.

Фактически проверенные frozen candidate IDs:

- `SBER_LONG_M5_POST_FIX_V1` / admission `c1646317-0988-5cf8-afcc-12664f441167` / run `4e8636c6-9770-5f09-82ee-afed5c7c37f4`;
- `BRQ6_SHORT_M5_POST_FIX_V1` / admission `ef56e385-c330-51fb-b04d-5f52ff50f16e` / run `531d6295-4a00-5422-a3b2-0789329dfe97`;
- `GLDRUBF_LONG_M5_POST_FIX_V1` / admission `ec28dd44-14f2-5288-af7e-fe3afdd165ad` / run `5905c56b-95e8-57d0-b4a3-1ca8378405dc`;
- `CNYRUBF_LONG_M5_POST_FIX_V1` / admission `7ca1713f-7ed0-5930-9087-50bd65a3ca51` / run `fb7218b1-7c83-5c04-9908-39d02e56ff3b`.

## Итоговый вердикт

**PARITY FAIL — идентичность кандидата V5 и исполняемого Paper-сигнала не доказана.**

На момент проверки в БД `0` записей `trade_outcome_oos_admission_v1.status_code='OOS_PASS'` и `0` активных профилей `entry_exit_runtime_profile_v1.status='ACTIVE'`. Поэтому фактической пары «прошедший V5 кандидат → исполненная Paper-сделка» сейчас не существует. Статический разбор также выявил критические расхождения, которые не позволят считать такую пару идентичной после будущего PASS.

Положительная часть: V5 фиксирует `symbol + strategy + side + candidate_code` и профиль параметров, применяет purge/embargo и Paper-gate сверяет эти идентификаторы. Это защищает от случайного продвижения другого кандидата, но не гарантирует одинаковое вычисление сигнала, признаков, исполнения и выхода.

## Scope и ограничения аудита

Проверены исходный код, systemd effective configuration и read-only состояние PostgreSQL. Не запускались research workers, replay, торговый pipeline или тесты, способные записывать события. Заявки не отправлялись, Live не включался. Фактическое повторное вычисление Paper-сделки невозможно: у четырёх веток нет ни одного OOS-наблюдения, ни одного PASS, активного runtime profile или Paper trade с их candidate code. Поэтому отсутствие фактической пары само по себе даёт **NOT PROVEN**, а найденные структурные различия повышают общий итог до **PARITY FAILED**.

Команды и read-only проверки:

- `git branch --show-current`, `git rev-parse HEAD`, `git status --short`;
- `systemctl show finam-paper-pipeline.service -p ExecStart -p Environment`;
- `psql` SELECT из `v5_post_fix_branch_registry_v1`, `trade_outcome_oos_admission_v1`, `v5_oos_run_v1`, `entry_exit_runtime_profile_v1`, `closed_trades`;
- `rg`, `nl -ba`, `sed` по research, runtime, execution, risk и exit modules;
- `git diff --check -- REPORT_PARITY_AUDIT.md`.

## Канонический фактический data flow и call graph

```text
Research
signals + closed_trades + market_bars
  -> build_entry_exit_optimizer_v1.py
  -> entry_exit_optimizer.py (_entry, simulate_variant)
  -> entry_exit_signal_shadow_pair_v2
  -> maintain_entry_exit_oos_admissions_v1.py
  -> trade_outcome_oos_admission_v1 + frozen_profile
  -> run_v5_purged_oos_worker_v1.py
  -> v5_oos_run_v1 / v5_oos_observation_audit_v1
  -> run_adaptive_regime_pilot_v1.py
  -> entry_exit_runtime_profile_v1

Runtime
market feed/live state
  -> run_market_pipeline.py
  -> StrategyStack(BreakoutReactiveStrategy, VWAPBandsMRStrategy)
  -> paper_pipeline.py (strategy-specific routes, filters, risk, OOS gate)
  -> optional adaptive_pending_entry worker + market_bars
  -> RiskEngine / futures adaptive risk / portfolio gates
  -> PaperExecutionEngine.execute (bid/ask + slippage + PaperCostModel)
  -> fill persistence / position projection
  -> ExitEngine + regime/time/session/risk overlays
  -> closed_trades + P&L attribution
```

Каноническим runtime entry-point фактически является `src/scripts/run_market_pipeline.py`, запущенный systemd с `--strategy strategy_stack --enable-filter-engine`. Код research расположен в `src/scripts/analytics` и `src/finam_core/analytics`. В дереве одновременно существуют верхнеуровневые `src/execution`, `src/core`, `src/analytics` и пакет `src/finam_core/*`; отсутствует единый manifest, доказывающий, что legacy namespaces не импортируются. Каталогов `src/marketcore` и `src/marketcore_os` в проверенном дереве не найдено. Это не доказывает ошибочный импорт, но оставляет namespace lineage **NOT PROVEN**.

## Матрица четырёх frozen V5-кандидатов

| Branch | Frozen identity | Freeze | OOS state | Specific parity blocker | Status |
|---|---|---|---|---|---|
| SBER LONG M5 | `MEAN_REVERSION_EQUITY / EXPERT_EQUITY_RANGE_RETEST / ADAPTIVE / 1.3 / 1.6 / trail 1.0R,0.8ATR` | 01.08 21:06 MSK | 0/20, COLLECTING | runtime strategy stack/feature lineage не совпадает; trailing теряется | **FAIL** |
| BRQ6 SHORT M5 | `BR_CONSERVATIVE_BREAKOUT / EXPERT_BR_RETEST_VOLUME / ADAPTIVE / 1.6 / 2.6 / trail 1.2R,1.0ATR` | 01.08 21:06 MSK | 0/20, COLLECTING | runtime не передаёт EXPERT_BR policy; futures risk сохраняет другую stop/take geometry | **FAIL** |
| GDU6 LONG M5 | `GOLD_TREND_BREAKOUT / EXPERT_GOLD_CONFIRM_MTF / ADAPTIVE / 1.7 / 2.7 / trail 1.2R,1.0ATR` | 01.08 21:06 MSK | 0/20, COLLECTING | runtime не передаёт M15 alignment/EXPERT_GOLD; futures geometry и trailing иные | **FAIL** |
| CNYRUBF LONG M5 | `CNY_REGIME_FUTURES / EXPERT_FX_RETEST_COST / ADAPTIVE / 1.4 / 2.0 / trail 1.0R,0.9ATR` | 01.08 21:06 MSK | 0/20, COLLECTING | registry M5, optimizer mapping CNY M1; EXPERT_FX и cost context не воспроизводятся | **FAIL** |

Все четыре admissions имеют `RUNNING/COLLECTING`, `observations_included=0`, `effective_observations=0`, minimum `20`, reason `WAITING_FUTURE_OBSERVATIONS`. `confirmation_after_ts`: SBER `2026-08-02 01:06:19+03`; остальные `03:06:19+03`.

## Матрица проверки

| № | Область | Статус | Краткий вывод |
|---|---|---|---|
| 1 | Признаки | **FAIL / Critical** | Research восстанавливает признаки по завершённым барам; runtime использует неполный payload/live state и теряет M15 alignment. |
| 2 | Источники данных | **FAIL / High** | Research читает `signals`, `closed_trades`, `market_bars`; runtime-сигнал рождается из live strategy stack, затем часть входа проверяется по `market_bars`. Единого snapshot ID нет. |
| 3 | Параметры | **FAIL / Critical** | stop/take копируются лишь частично; trailing теряется при активации; для фьючерсов stop/take профиля намеренно не применяются. |
| 4 | Вход | **FAIL / Critical** | Исследуемые strategy codes не являются теми классами, которые основной runner вызывает в `strategy_stack`; ADAPTIVE в runtime вызывается с другой policy. |
| 5 | Выход | **FAIL / Critical** | Research моделирует stop/take/trailing/horizon; runtime добавляет regime, stall/time, hard-max и session-end exits с другими параметрами. |
| 6 | Комиссии | **FAIL / High** | Research использует наблюдаемую комиссию с floor; runner создаёт execution engine с `commission=0.0`, а дальнейшие runtime cost models отдельны. Единого economics object нет. |
| 7 | Фильтры | **FAIL / High** | Research включает `RISK_REJECTED`; runtime такие сигналы не исполняет и применяет дополнительные embargo/filter gates. |
| 8 | Risk gates | **FAIL / Critical** | Runtime futures policy может изменить stop/take/qty или заблокировать вход; research simulator этого решения не воспроизводит. |
| 9 | Timestamp | **FAIL / High** | Research привязан к `s.ts/s.created_at`; runtime pending entry записывает `clock_timestamp()`, меняя границу будущих баров. |
| 10 | End-to-end идентичность | **FAIL / Critical** | Нет общего immutable execution specification и нет replay-теста, сравнивающего research decision с Paper decision byte-for-byte. |

## Найденные расхождения

### P0-1. Генератор Paper-сигнала не идентичен исследуемой стратегии

- **Файл/строки:** `src/scripts/run_market_pipeline.py:317-334`.
- **Факт:** основной `strategy_stack` содержит `BreakoutReactiveStrategy` и `VWAPBandsMRStrategy(window=150,k=1.5,stop_pct=0.004,take_pct=0.0)`. V5 исследует коды `MEAN_REVERSION_EQUITY`, `VOLATILITY_BREAKOUT_EQUITY`, `BR_CONSERVATIVE_BREAKOUT`, `NG_CONSERVATIVE_BREAKOUT_M1`, `CNY_REGIME_FUTURES`, `USD_REGIME_FUTURES`, `GOLD_TREND_BREAKOUT` (`src/scripts/analytics/build_entry_exit_optimizer_v1.py:25-33`).
- **Влияние:** V5 оптимизирует последствия уже сохранённого сигнала, но не доказывает, что runtime заново породит тот же сигнал на тех же данных.
- **Риск:** **Critical**.
- **Исправление:** ввести единый versioned `SignalSpecification` и один вызываемый модуль генерации сигнала для research/replay/runtime; хранить `spec_hash`, feature snapshot и source-bar IDs в каждой записи V5 и Paper.

### P0-2. ADAPTIVE использует разные признаки и разные policy

- **Файлы/строки:** `src/finam_core/analytics/entry_exit_optimizer.py:103-156,163-207`; `src/scripts/analytics/build_entry_exit_optimizer_v1.py:208-240`; `src/finam_core/pipelines/paper_pipeline.py:5667-5678`.
- **Факт:** research передаёт `policy_code` кандидата и `higher_timeframe_aligned`, рассчитанный по завершённым M15-барам. Runtime не передаёт ни `policy_code`, ни `higher_timeframe_aligned`; вызывается default `GENERIC`. Runtime также подставляет defaults `atr_percentile=0.5`, `relative_volume=1.0`, `cost_to_atr=0.0`.
- **Влияние:** один кандидат может получить `SKIP/CONFIRM_1/RETEST_3/IMMEDIATE` в research и другое решение в Paper.
- **Риск:** **Critical**.
- **Исправление:** сохранять полный frozen context schema и `policy_code` в runtime profile; вычислять признаки общей функцией по тем же закрытым барам; запрещать fallback defaults для продвинутого профиля.

### P0-3. Параметры trailing теряются при продвижении

- **Файлы/строки:** frozen V5 profile — `src/scripts/analytics/build_entry_exit_optimizer_v1.py:183-197`; активация Paper — `src/scripts/run_adaptive_regime_pilot_v1.py:236-248`; чтение runtime — `src/finam_core/pipelines/paper_pipeline.py:5643-5653,5740-5748`.
- **Факт:** V5 фиксирует `trail_after_r` и `trail_atr`, но activation INSERT записывает для обоих `NULL`. Runtime способен их прочитать, однако получает потерянные значения.
- **Влияние:** профиль, прошедший V5 с trailing, исполняется без доказанного trailing-поведения.
- **Риск:** **Critical**.
- **Исправление:** копировать весь frozen profile атомарно, сверять canonical JSON/hash до активации и fail closed при любом несовпадении.

### P0-4. Для фьючерсов stop/take V5 не становятся Paper stop/take

- **Файл/строки:** `src/finam_core/pipelines/paper_pipeline.py:5659,5734-5749`.
- **Факт:** при `symbol.endswith('@RTSX')` устанавливается `futures_contract_risk_preserved`; stop/take из активного entry/exit profile не записываются в intent.
- **Влияние:** BR/NG/CNY/USD/GOLD могут пройти V5 с одной геометрией риска, а Paper использует геометрию другого futures risk calibrator.
- **Риск:** **Critical**.
- **Исправление:** единый contract-aware frozen risk object должен владеть entry, stop, take, trail, multiplier, tick rounding и sizing и использоваться обоими контурами.

### P0-5. Research и runtime имеют разные правила выхода

- **Файлы/строки:** research — `src/finam_core/analytics/entry_exit_optimizer.py:211-274`; runtime — `src/finam_core/strategy/exit_engine.py:16-72,76-110`; интеграция — `src/finam_core/pipelines/paper_pipeline.py:3173-3248,3284-3454`.
- **Факт:** research моделирует stop-first OHLC, take, trailing от предыдущего экстремума и `HORIZON_MARK`. Runtime дополнительно применяет regime invalidation, minimum hold, hard max hold с trend extension, operator-governed time exit и session-end exit; базовый `ExitEngine` имеет собственные max bars/breakeven/trailing/stall параметры.
- **Влияние:** цена, время и причина закрытия, а значит net R, не совпадут даже при одинаковом входе.
- **Риск:** **Critical**.
- **Исправление:** вынести один deterministic `ExitPolicy.evaluate(completed_bar,event_state)`; research должен replay той же state machine и всех аварийных правил либо кандидат должен явно доказать отдельный overlay и учитывать его в OOS.

### P0-6. Runtime risk policy может переписать кандидата

- **Файл/строки:** `src/finam_core/pipelines/paper_pipeline.py:5489-5608` (futures adaptive risk до entry/exit profile), затем `5610-5751`.
- **Факт:** runtime может изменить quantity/stop/take или заблокировать сигнал до применения оптимизированного профиля; для фьючерсов его геометрия затем сохраняется.
- **Влияние:** исполняется не frozen V5 risk configuration.
- **Риск:** **Critical**.
- **Исправление:** формализовать порядок overlays в frozen execution spec и воспроизводить его в research; сравнивать итоговый normalized intent hash, а не только candidate code.

### P1-1. Research включает сигналы, которые Paper отверг

- **Файл/строки:** `src/scripts/analytics/build_entry_exit_optimizer_v1.py:310-334`, особенно `329`.
- **Факт:** исходная выборка содержит `s.status IN ('FILLED','RISK_REJECTED')`.
- **Влияние:** кандидат оценивается на возможностях, недоступных runtime из-за risk gates; частота и распределение сделок не совпадают.
- **Риск:** **High**.
- **Исправление:** разделить `signal-quality research` и `executable-policy research`; для parity/OOS использовать только события, прошедшие frozen runtime gates, либо replay всех gates по point-in-time состоянию портфеля.

### P1-2. Нет единого источника признаков

- **Файлы/строки:** research context — `src/scripts/analytics/build_entry_exit_optimizer_v1.py:208-240`; runtime context — `src/finam_core/pipelines/paper_pipeline.py:5660-5675`.
- **Факт:** research заново вычисляет ATR percentile, relative volume и M15 alignment из `market_bars`; runtime берёт значения из intent/live state и допускает defaults. Regime также берётся из разных полей.
- **Влияние:** feature drift и silent fallback без аудита.
- **Риск:** **High**.
- **Исправление:** point-in-time feature snapshot с schema/version/hash; и research, и runtime должны потреблять один snapshot, а не пересчитывать независимо.

### P1-3. Timestamp pending-entry сдвинут к времени обработки

- **Файлы/строки:** research timestamp — `src/scripts/analytics/build_entry_exit_optimizer_v1.py:316,345,353-357`; runtime insert — `src/finam_core/pipelines/paper_pipeline.py:5682-5691,5720-5730`; worker — `src/scripts/run_adaptive_pending_entry_worker_v1.py:23-38`.
- **Факт:** research использует timestamp сигнала; runtime сохраняет `signal_ts=clock_timestamp()`, после чего выбирает бары `ts > signal_ts`. Задержка pipeline меняет набор подтверждающих баров.
- **Влияние:** разные CONFIRM/RETEST решения и entry price.
- **Риск:** **High**.
- **Исправление:** передавать immutable event timestamp и last-completed-bar timestamp; хранить processing timestamp отдельно; бар выбирать по source bar ID.

### P1-4. Комиссионная модель не едина

- **Файлы/строки:** research economics — `src/scripts/analytics/build_entry_exit_optimizer_v1.py:67-98`; runner — `src/scripts/run_market_pipeline.py:317-318`; net R — `src/finam_core/analytics/entry_exit_optimizer.py:267-274`.
- **Факт:** research использует commission из закрытой Paper-сделки либо floor (для futures минимум один adverse tick на сторону, для equities 8 bps). Верхнеуровневый Paper engine создаётся с `commission=0.0`; фактические комиссии рассчитываются другими runtime-слоями и environment-параметрами.
- **Влияние:** economics threshold, `cost_to_atr`, net R и PASS могут отличаться от Paper P&L.
- **Риск:** **High**.
- **Исправление:** единый versioned `ExecutionCostModel` с instrument spec, тарифом, spread/slippage и rounding; сохранять `cost_model_hash` в V5 и Paper.

### P1-5. Research timeframe/horizon жёстко задан, runtime timeframe допускает fallback

- **Файлы/строки:** `src/scripts/analytics/build_entry_exit_optimizer_v1.py:25-45`; `src/finam_core/pipelines/paper_pipeline.py:5690,5716-5719`.
- **Факт:** research задаёт M1/M5 и 48–240 баров по strategy; runtime берёт timeframe из intent/features или выводит его по типу инструмента.
- **Влияние:** подтверждение входа и длительность исследования могут относиться к другой временной сетке.
- **Риск:** **High**.
- **Исправление:** timeframe и horizon включить в frozen profile и запретить runtime inference/fallback.

### P1-6. Runtime filters/embargo не replay в исследовании

- **Файл/строки:** runtime pre-persistence embargo — `src/finam_core/pipelines/paper_pipeline.py:5760-5776`; promoted OOS и pilot gates — `5880-6073`.
- **Факт:** runtime проверяет открытую позицию, cooldown, OOS admission, regime и pilot budgets. Исследовательский simulator оценивает независимо дедуплицированные сигналы, но не воспроизводит point-in-time portfolio state и все runtime gates.
- **Влияние:** число и последовательность фактически исполнимых сделок отличаются.
- **Риск:** **High**.
- **Исправление:** общий pure gate evaluator с сериализованным state snapshot; V5 считать на событиях после тех же gates и в той же последовательности.

### P2-1. CONFIRM_1/RETEST_3 формулы в целом совпадают, но доказательство не автоматизировано

- **Файлы/строки:** research — `src/finam_core/analytics/entry_exit_optimizer.py:163-207`; runtime helper — `src/finam_core/execution/adaptive_pending_entry_v1.py:15-41`.
- **Факт:** close confirmation, 0.70 ATR runaway guard, 0.20 ATR retest tolerance и три бара совпадают. Однако это дублированный код, а не общий implementation; `signal_ts` и ADAPTIVE routing различаются.
- **Влияние:** текущая локальная формула близка, но может разойтись при следующем изменении.
- **Риск:** **Medium**.
- **Исправление:** использовать одну функцию в обоих контурах и добавить golden parity tests по LONG/SHORT, gap, ambiguous bar и missing bars.

## Что уже защищено корректно

1. Frozen V5 request сохраняет candidate code, entry mode, stop/take/trailing и temporal isolation: `src/scripts/analytics/build_entry_exit_optimizer_v1.py:183-197`.
2. Research использует только завершённые до сигнала бары для контекста: `src/scripts/analytics/build_entry_exit_optimizer_v1.py:208-240`.
3. Future bars выбираются после timestamp сигнала и только завершённые: `src/scripts/analytics/build_entry_exit_optimizer_v1.py:351-362`.
4. OHLC-simulation консервативна при одновременном stop/take и не использует текущий high для предварительного поднятия trailing stop: `src/finam_core/analytics/entry_exit_optimizer.py:243-266`.
5. Paper OOS gate сопоставляет symbol, strategy, side и candidate code и проверяет `confirmation_after_ts`: `src/finam_core/pipelines/paper_pipeline.py:5912-5953`.
6. При ошибке активного профиля runtime fail closed, а не делает незапрофилированный немедленный вход: `src/finam_core/pipelines/paper_pipeline.py:5752-5758`.

## Runtime evidence и SQL lineage

Проверенные SQL-объекты:

- `analytics.v5_post_fix_branch_registry_v1` — immutable registry четырёх веток; хранит symbol, strategy, side, timeframe, candidate, entry/stop/take/trail и freeze timestamp. Не хранит git SHA, config hash, feature schema hash или algorithm artifact hash.
- `analytics.trade_outcome_oos_admission_v1` — admission и JSON frozen request.
- `analytics.v5_oos_run_v1` — purge/confirmation timestamps, счётчики, verdict и `source_version='V5_PURGED_OOS_WORKER_V2'`.
- `analytics.v5_oos_observation_audit_v1` — аудит включения/исключения наблюдений.
- `analytics.entry_exit_runtime_profile_v1` — runtime overrides; активных строк на срезе **0**.
- `signals`, `market_bars`, `closed_trades` — source research и результаты Paper; Paper-сделок с одним из candidate codes **0**.

`run_v5_purged_oos_worker_v1.py:28-48,147-162` сопоставляет frozen candidate и отсекает события до `confirmation_after_ts`. Это доказывает admission-level temporal gate, но не доказывает, что upstream shadow event был произведён тем же runtime algorithm. В systemd фактически установлены `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`, `ENABLE_PAPER_FILLS=1`; основной runner содержит десять символов и `strategy_stack`. Live не активен.

Сопоставление нескольких фактических Paper-сделок с кандидатами не выполнено не из-за пропуска аудита, а из-за отсутствия таких сделок (`paper_candidate_trades=0`). Следовательно runtime evidence для signal/order/fill/exit/P&L каждого frozen candidate — **NOT PROVEN**.

## Costs and P&L coverage

| Компонент | Research | Paper runtime | Parity |
|---|---|---|---|
| Broker/exchange commission | observed closed-trade commission либо floor | `PaperCostModel`, ENV broker/exchange rates и minimum commission | NOT PROVEN: разные источники и момент расчёта |
| Spread | не моделируется отдельно; futures floor через ticks | bid/ask spread участвует в fill | FAIL |
| Slippage | stop slippage ticks; conservative gap | `slippage_coef=0.25` от spread | FAIL |
| Market impact | отсутствует | отдельный slippage model существует, применение данным маршрутом не доказано | NOT PROVEN |
| Funding/carry/variation margin | отсутствуют | явное применение к P&L кандидата не найдено | NOT PROVEN |
| Tick/contract multiplier | contract spec в research economics | runtime contract/futures policies | NOT PROVEN как одна и та же версия spec |
| Lot/quantity rounding | не является частью `simulate_variant` | runtime risk/broker constraints | FAIL для распределения P&L |
| Gross/Costs/Net | `net_r=(gross-roundtrip_cost)/risk` | fill costs, commission, tax и RUB attribution отдельными слоями | FAIL |

## Filter, risk и sizing classification

**A — исследуемая стратегия:** ADAPTIVE volume/ATR/regime/cost/MTF gates, entry mode, stop/take/trail. Именно здесь найдены разные context/policy и потеря trailing.

**B — эксплуатационные Paper-ограничения:** OOS admission, max pilot trades, maximum open positions, kill/live switches, session-end safety. Они допустимы только если не меняют оцениваемую экономику либо отдельно моделируются.

**C — ограничения, меняющие распределение относительно research:** FilterEngine, active-universe, duplicate/cooldown, position eligibility, futures adaptive risk, quantity rounding, cluster/portfolio exposure, time/regime exits. Сейчас они не replay point-in-time, поэтому parity FAIL.

Для liquidity, spread, volatility, regime, event/news, stale data, market shock, feature freshness, instrument/portfolio eligibility не найден единый ordered gate manifest с threshold/hash, общий для research и runtime. Нельзя подтвердить ни одинаковый состав и порядок, ни fail-open/fail-closed поведение. Где runtime имеет явный promoted-profile failure, он fail-closed (`paper_pipeline.py:5752-5758`); это локальное свойство, не parity всей воронки.

## Timestamp semantics

Research трактует `coalesce(signals.ts,signals.created_at)` как signal time и выбирает `market_bars.ts > signal_time`, ограничивая последний бар `now-timeframe`. Feature context берётся до `entry_ts-timeframe`; M15 alignment требует `ts + 15 minutes <= entry_ts`. Runtime имеет event/live state, processing time и pending entry, но сохраняет `clock_timestamp()` вместо исходного event time. Bar open/close convention таблицы не закреплена общим schema hash; ingestion/order/fill clocks не связаны одним trace ID со frozen observation. Timezone в PostgreSQL timestamptz сохраняется, UI/systemd работает MSK, однако одинаковое округление и latency tolerance не специфицированы. Поэтому point-in-time parity — FAIL.

## Version и provenance gaps

Ни один из четырёх frozen registry rows не содержит:

- git commit/hash исследовательского executable;
- config/environment hash;
- feature schema/version/hash;
- code artifact/container hash;
- contract-spec version/hash;
- cost-model version/hash;
- ordered filter/risk manifest hash.

Есть branch/admission/run IDs и worker source version, но этого недостаточно для воспроизводимости. Совпадение strategy name/candidate name не считается доказательством.

## Блокирующие условия перед micro-live

1. Не менее одного фактического OOS PASS и затем controlled Paper pilot — сейчас их нет.
2. Устранены все P0-разрывы и создан immutable `ExecutionSpec` с hash.
3. Получен byte-for-byte parity replay на новых событиях: features, decision, entry, sizing, exits, costs, net P&L.
4. Runtime сохраняет source event/bar IDs и не подменяет event time processing clock.
5. Все cost/risk/filter overlays либо входят в research replay, либо доказано не меняют выборку и экономику.
6. Автоматический `PARITY_BLOCKED` при mismatch и проверенный rollback active profile.
7. Live остаётся выключенным до отдельной micro-live readiness проверки.

## Условия, необходимые для доказанной parity

Продвижение в Paper должно оставаться заблокированным, пока не выполнены все условия:

1. Один immutable `ExecutionSpec` включает strategy/version, feature schema, source bar IDs, timeframe, policy, entry, exit, costs, filters, gates, contract spec и timestamps.
2. V5 сохраняет canonical JSON + hash этого spec; Paper принимает только тот же hash.
3. Research и runtime используют одни pure functions для features, adaptive routing, pending entry, exit policy, costs и gates.
4. Никакой default/fallback не разрешён для promoted candidate; отсутствующий признак означает reject.
5. Есть replay harness: каждый V5 observation повторно проходит runtime-код и сравниваются signal decision, effective entry, stop, take, trail, qty, exit, costs и net R.
6. Golden tests покрывают LONG/SHORT, equities/futures, gaps, stop+take в одной свече, trailing, regime/time/session exits и rejected risk gates.
7. Перед активацией выполняется автоматический assertion: `frozen_spec_hash == runtime_spec_hash`; несовпадение переводит workflow в `PARITY_BLOCKED`.

## Ближайший порядок исправления

1. **P0:** единый execution spec/hash и fail-closed parity gate.
2. **P0:** устранить потерю `policy_code`, M15 alignment и trailing; запретить отдельную futures geometry.
3. **P0:** общий exit state machine для research/runtime.
4. **P1:** общий cost model и point-in-time feature snapshot.
5. **P1:** replay runtime filters/risk/portfolio state; исключить недоступные `RISK_REJECTED` из executable OOS.
6. **P1:** сохранить source event/bar timestamps вместо `clock_timestamp()`.
7. **P2:** end-to-end parity test на историческом событии до разрешения любой Paper-активации.

## Заключение

Текущая система подтверждает **статистический результат варианта поверх исторического потока сигналов**, но пока не подтверждает **идентичность исполняемой торговой политики**. Наиболее опасные разрывы — другой генератор сигнала, различный ADAPTIVE context/policy, потеря trailing, отдельная futures risk geometry и дополнительные runtime exits. До их устранения V5 PASS нельзя трактовать как доказательство того, что Paper исполняет исследованного кандидата.

## Компактный итог по кандидатам

| Candidate | Features | Data | Parameters | Entry | Exit | Costs | Filters | Risk | Time | Code path | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SBER LONG / EXPERT_EQUITY_RANGE_RETEST | FAIL | NOT PROVEN | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| BRQ6 SHORT / EXPERT_BR_RETEST_VOLUME | FAIL | NOT PROVEN | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| GDU6 LONG / EXPERT_GOLD_CONFIRM_MTF | FAIL | NOT PROVEN | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** |
| CNYRUBF LONG / EXPERT_FX_RETEST_COST | FAIL | NOT PROVEN | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | **FAIL** |

**Общий вердикт: PARITY FAILED.** Даже без найденных расхождений результат был бы `PARITY NOT PROVEN` из-за отсутствия provenance hashes и runtime observations; обнаруженные различия способны изменить signals, fills, exits, sizing и P&L, поэтому применён более строгий статус `FAILED`.
