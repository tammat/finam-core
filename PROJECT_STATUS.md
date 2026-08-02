# MarketCore / finam-core — текущий статус

Дата среза: 02.08.2026, МСК

Ветка: `codex/research-edge-v5`

Проверенный HEAD: `3a138c82fe78d7ebb741a9337d96814afb46c3cf`

Статус: `PAPER_AND_SHADOW_ACTIVE__V5_OOS_COLLECTING__LIVE_BLOCKED`

## Резюме

MarketCore является работающей Paper/Shadow-исследовательской платформой с
развитым fail-closed риск-контуром и V5 OOS-валидацией. Полностью автоматическая
прибыльная торговля не подтверждена: ни одна из четырёх замороженных V5-веток
ещё не получила будущих независимых наблюдений и OOS PASS.

## Runtime

- Active/running: `finam-paper-pipeline`, `finam-paper-safe`,
  `finam-research-runtime`, `finam-analytics-supervisor`, `finam-governance`,
  `finam-orchestrator-safe`, `finam-projection-worker`, `marketcore-ui-shell`,
  `marketcore-kg-api`.
- Основной Paper universe: BRQ6, NGQ6, CNYRUBF, USDRUBF, GDU6, SBER, GAZP,
  LKOH, NVTK, VTBR.
- Последний preflight: `ATTENTION`, причина `HOST_LOAD_HIGH:3.78`; структурные
  проверки четырёх V5-источников прошли.

## Safety и execution

- `EXECUTION_ENABLED=0`.
- `REAL_TRADING_ENABLED=0`.
- `REAL_EXECUTION_ENABLED=0`.
- Live route dispatcher выключен.
- Broker trailing работает в `DRY_RUN`.
- `public.orders`: 0 записей; реальные заявки MarketCore не отправлялись.
- `real_portfolio_positions`: 11 ненулевых синхронизированных брокерских
  позиций; это не позиции, открытые MarketCore.

## Данные и Feature Store

- Для основных инструментов имеются M1/M5/M15/H1; последние торговые бары —
  31.07.2026.
- `public.feature_snapshots`: 393091 строк, 18 инструментов, последний bar
  31.07.2026 23:45 МСК.
- Известные разрывы: M1 NVTK/VTBR заканчивается 29.07; H1 основных инструментов
  в основном заканчивается 29.07, NG H1 — 25.07.
- `analytics.feature_store_health_v1` содержит устаревший снимок от 04.07 и
  поэтому его `HEALTHY` нельзя считать актуальным доказательством здоровья.

## Signal funnel

Последний снимок 31.07.2026:

- evaluations: 94302;
- уникальные closed-bar opportunities: 18261;
- оценено в Shadow: 606 (3,32%);
- допущено к Paper-заявке: 1028 (5,63%);
- ACK / fill / trade: 1028 / 1028 / 1028.

Главное узкое место — переход от большого числа возможностей к сопоставимой
Shadow-оценке, а не исполнение Paper.

## Research и V5 OOS

- Активные workflow: 25 `SHADOW_ACCUMULATION`, 4 `V5_OOS_COLLECTING`.
- `expensive_gates_pass=true`: 0.
- `v5_oos_pass=true`: 0.
- Четыре frozen V5-ветки: Brent SHORT, CNY LONG, Gold LONG, SBER LONG.
- Для всех статус OOS: `COLLECTING / WAITING_FUTURE_OBSERVATIONS`.
- Включено будущих независимых наблюдений: 0 из минимальных 20 на ветку.
- Граница подтверждения установлена 02.08.2026; рынок после неё ещё не
  открывался, поэтому нулевое накопление ожидаемо.

## Paper V5

Чистые V5-когорты: 102 закрытые Paper-сделки, но максимум за четыре торговых
дня. Предварительно положительны Brent LONG (20 сделок, +1581,40 ₽, PF 1,65) и
equity mean reversion LONG (58 сделок, +109,71 ₽, PF 2,06). Это не OOS PASS:
период короткий, а текущие frozen admission могут относиться к другим
направлениям и профилям.

## Статистическая защита

Работают: purging, embargo, `confirmation_after_ts`, запрет повторного
использования наблюдений, event clustering, time-shifted placebo,
Gross/Costs/Net, block bootstrap, family-wise threshold, MDE, контроль
концентрации прибыли, последовательный Paper rollback.

## Риск

Текущая DB-policy: риск на сделку 1%, дневной лимит 2%, drawdown 3%, доля
инструмента 10%, gross exposure 100%, margin utilisation 65%, кластер 60%.
Реализованы portfolio/cluster exposure, correlation, liquidity/spread,
market-event и market-shock gates, kill switch и fail-closed проверки.

## Неполные контуры

- `analytics.swing_candidate_lifecycle_v1`: 0 строк — Swing архитектурно есть,
  но фактически не накапливает доказательства.
- `analytics.edge_strategy_degradation_v1`: 0 строк.
- `analytics.strategy_degradation_state_v1`: 0 строк.
- Несколько strategy-классов являются адаптерами-заглушками, а исполняемая
  логика распределена между pipeline, scripts и DB-policy. Требуется строгий
  parity audit research-кандидата и runtime-сигнала.
- В репозитории сосуществуют `src/finam_core`, `src/marketcore`,
  `src/marketcore_os` и legacy namespaces; это увеличивает риск использования
  неканонического модуля.

## Что отделяет от автоматической прибыльной торговли

1. Будущие V5 OOS наблюдения и хотя бы один OOS PASS.
2. Стабильность edge на нескольких режимах и торговых периодах после издержек.
3. Доказанная идентичность Research → Paper → broker execution.
4. Работающий operational degradation/rollback loop.
5. Исправленная freshness-диагностика Feature Store и пробелы market data.
6. Минимальный Paper pilot, затем micro-live с минимальным размером и полным
   reconciliation; только после этого может обсуждаться Live.

## Ближайший приоритет

Не расширять стратегии. В понедельник подтвердить поступление новых M1/M5/M15,
включение наблюдений в четыре frozen V5 OOS-run и сохранение точной идентичности
candidate code. Параллельно исправить только мониторинговые разрывы Feature
Store/degradation и довести одну Swing-ветку до Forward Shadow.

## Итоговая оценка

- Paper/Shadow engineering: 7/10.
- Statistical methodology: 7/10.
- Operational monitoring: 5/10.
- Доказанность edge: 2/10.
- Live readiness: не готово; Live корректно заблокирован.
