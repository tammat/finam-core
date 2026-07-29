# CHECKPOINT_RESEARCH_PAPER_CONTOUR_V1

Дата: 28.07.2026, МСК
Git branch: codex/research-edge-v5
Verified code HEAD: 810cb2cb96fb24e158520cdac19fc9a395fe00c0
Статус: V5_RUNTIME_RESTORED_EDGE_ACCUMULATION_ACTIVE

## Подтверждено

- Scope bootstrap V5 восстановлен для акций и фьючерсов.
- Generic Paper direction gate fail-closed добавлен.
- Реальное исполнение отключено.
- Закрытые факты отделены от чистой V5-методологии.
- Operator Control использует source-backed статусы исключения.
- Текущая NGQ6 Paper-позиция открыта 20:07:01 МСК в `range_normal_vol` и не является контртрендовой.
- Restart recovery ExitEngine сохраняет фактическое время открытия из Paper lifecycle.
- После первого runtime-check устранена вторичная перезапись времени на первом quote: restore теперь также выставляет `last_qty` восстановленной позиции.

## VERDICT

- TEST_ENTRY_GATE_PORTFOLIO_SCOPE_V1_OK
- TEST_PAPER_CLOSED_TRADE_MATERIALIZER_V2_OK
- TEST_GLOBAL_PAPER_DIRECTION_GATE_V1_OK
- TEST_CONTROL_COMPACT_RESEARCH_STATUS_V1_OK
- TEST_PAPER_EXIT_PROJECTION_RESTORE_V1_OK (`4 passed` совместно со scope/direction tests)
- V5_CONTRACT_SUITE_OK (`61 passed`)
- V5_CORE_VERIFIED_FULL_TREE_NOT_CANONICAL

## Dirty-tree audit

- Canonical-ветка очищена; непроверенный слой вынесен без потерь.
- Quarantine: `codex/quarantine-pre-v5-wip-20260728`, commit `f91941a7`.
- Quarantine не является baseline: расширенная проверка дала 69 passed / 5 failed, atomic runtime contract — ещё 5 незавершённых assertions.
- Runtime snapshots не включены; backup/log сохранены в `/tmp/finam-core-local-archive-20260728`.

## Canonical manifest

- Явный staged manifest: 95 файлов, без snapshots/logs/locks/backups и UI/legacy WIP.
- Проверен отдельный checkout содержимого git index: `61 passed`.
- Safety diff: execution/real execution только отключены; секреты не обнаружены.
- Эталонный V5 baseline создан и дополнен проверенными атомарными коммитами.

## Canonical V5 additions

- `d8e37ff6`: воспроизводимый project context и workspace hygiene.
- `3def889f`: отсутствовавшая схема portfolio risk/degradation.
- `1b781d7c`: отдельный candle-driven swing-контур, H1/H4/D1.
- `810cb2cb`: explicit adaptive entry constraints имеют приоритет над DB profile defaults.
- Финальный объединённый Swing/Risk acceptance: `47 passed`; master-context verifier OK.
- Runtime/migrations/services не запускались.

## Intraday canonical contour

- Intraday M1/M5 является обязательной частью V5 наряду со swing H1/H4/D1.
- BR/NG state exits используют завершённые M1; остальные intraday-инструменты — завершённые M5.
- Virtual stop/trailing проверяется на quote, но bar counters/regime invalidation не являются quote-driven.
- Clean-tree acceptance: `34 passed` по regime, scope, direction, closed-bar exit, materializer, restart restore, virtual trailing и Paper safety.
- Последний monotonic trailing code присутствует в canonical HEAD; runtime reload verification всё ещё требуется.

## Runtime verification 21:27 МСК

- PID `3754387`; pipeline и Paper Safe active.
- `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`.
- Persisted-bar reconstruction для NGQ6: `30` завершённых M1 после входа; reset до `1` устранён в code/SQL path.
- Фактический in-memory log ожидается: provider не дал первой котировки, watchdog reconnect не восстановил события.
- Ingestion также fail-stop на `2xEQT@MISX`; один invalid symbol блокирует успешное завершение timeframe/cycle.
- Следующий приоритет: instrument-level fail isolation в ingestion, затем повторная runtime-проверка первого quote и monotonic trailing.

## Runtime verification 21:34 МСК

- Pipeline PID `3770551`, ingestion PID `3770566`, Paper Safe active.
- Первая котировка пришла; NGQ6 projection восстановлена в PM с qty `1`.
- Restore-query error устранён; persisted M1 clock reconstructs `30` bars after entry.
- `2xEQT@MISX` fail-isolated после одного NOT_FOUND; следующие инструменты продолжают обновляться.
- BRQ6 M1 ingestion успешен; equity M5 readiness контролируется отдельно.
- Реальное исполнение отключено. Следующее доказательство: первое post-reload улучшение virtual stop и новое чистое intraday/equity закрытие.

## Runtime verification 21:36–21:37 МСК

- Pipeline PID `3782708`; first quote и projection restore успешны.
- NGQ6 state exit: `regime_invalidation_long`, persisted `bars_held=40`, Paper SELL 1 @ `2.71675`.
- Новая BRQ6 LONG: BUY 1 @ `84.1825`, initial virtual trailing stop `83.77`, dry-run only.
- Broker trailing errors после старта отсутствуют; safety flags неизменны.
- NG closed-trade materialization и первое чистое equity V5-закрытие остаются следующими наблюдаемыми фактами.

## Candle-state exit

- Quote не увеличивает bars_held.
- BR/NG exit-state: закрытые M1; остальные: закрытые M5.
- Confirmed fresh CANDLE_REGIME_V3 invalidation закрывает позицию против режима.
- Virtual Paper trailing применяется внутри ExitEngine без broker route.
- Energy time limit: 60 completed M1 bars, только safety net.
- NG M1 policy lookup исправлен через точное strategy assignment.
- `TEST@MISX` удалён из V5 projection/lifecycle, verified 0/0.
- Tests: 66 passed.
- Требуется перезапуск только `finam-paper-pipeline.service` и runtime-проверка BR.

## Runtime 21:00:21 МСК

- PID 3638452 active/running; real execution remains disabled.
- BR: restored age 1365.959 sec, completed M1 bars=1, virtual stop applied.
- NG: restored age 223.582 sec, pre-entry bar excluded, virtual stop applied.
- No broker trailing block after new PID.
- Clean V5 closed=1; open V5 futures positions: BR=1, NG=1.
- Duplicate virtual-stop writes suppressed in code; requires one final reload for noise reduction only.
- Reload 21:02:56 выявил потерю local trailing cache между lifecycle routes; общий ExitEngine state назначен authoritative monotonic stop. Tests: 12 passed, awaiting reload.

## Следующий checkpoint

1. Подтвердить блокировку следующего контртрендового сигнала в журнале.
2. Перезапустить pipeline и подтвердить, что возраст открытой NG-позиции не сбросился.
3. Получить первое чистое V5-закрытие по акциям и фьючерсам.
4. Проверить автоматическое увеличение точной связки и OOS routing.

## Runtime verification 20:24:59 МСК

- finam-paper-pipeline PID 3482540 active/running.
- marketcore-ui-shell PID 3482542 active/running.
- `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`.
- UI 18080: clean=0, excluded=4, open_paper=1.
- UI statuses: BR countertrend blocked; NGN6 stale contract.

Коммит не создан: рабочее дерево содержит посторонние незакоммиченные изменения.

## Market-data freshness 21:52–21:57 МСК

- Active watch universe: 68 точных targets — 64 M1 и 4 M5.
- Старый ingestion loop игнорировал timeframe каждой строки и расширял universe
  до M1/M5/H1 для каждого символа; это задерживало обновление V5.
- Исправленный loop выполняет только сохранённые `symbol × timeframe` и сразу
  пропускает `BTCUSD`/`ETHUSD` как `MISSING_MIC`.
- Static/runtime-plan verification: targets=68, valid=66, skipped=2; tests=3 passed.
- Deployment state: файлы обновлены, но service PID `3783032` ещё старый, потому
  что sudo требует интерактивный пароль. Требуется операторский restart ingestion.
- Safety state не менялся; real execution disabled. Чистое накопление V5 уже
  продолжается pipeline, а ускоренный bars cycle требует проверки после restart.

## Market-data freshness runtime verified 21:57–22:00 МСК

- Loaded PID: `3878185`, active/running since 21:57:46.
- Verified first targets: BRQ6/NGQ6 M1, SBER/GAZP/LKOH M1, NVTK/VTBR M5;
  all seven steps completed successfully before the remaining scout universe.
- Observed DB age: M1 137 sec, M5 197 sec at the same measurement point.
- V5 freshness is no longer held behind unrelated slow or invalid instruments.
- Verdict: `V5_FRESH_DATA_ACCUMULATION_ACTIVE`; real execution remains disabled.

## Auto-edge and governed UI audit 22:02–22:08 МСК

- Root scheduler blocker isolated: unsupported
  `HIERARCHICAL_EVIDENCE_ROUTER_V1` is persisted as FAILED configuration evidence
  without aborting independent allowlisted research jobs.
- Runtime advanced to `SESSION_EXECUTION_EDGE_V2`; previous immediate queue-cycle
  failure at the unsupported executor no longer occurs.
- Tests: 5 passed; real execution and live promotion remain disabled.
- UI verdict: `PARTIAL_CONTROL`. Research exposes several actions, but Control
  Center lacks canonical run/cancel state and some rendered commands have no
  governed handler. Next checkpoint is `V5_EDGE_CONTROL_READ_MODEL_V1`.

## V5 Edge Control read model 22:09–22:16 МСК

- Canonical registry now builds compact Control V3 directly.
- Read model covers scheduler, recent jobs, governed queue, edge process, V5
  freshness, clean cohorts and OOS readiness.
- Minimal UI: one contextual RUN/CANCEL slot plus REFRESH.
- No click means autonomous operation continues. Manual cancellation is scoped
  to the same non-system actor and cannot cancel `system.scheduler` requests.
- Server-side render verified; 8 focused tests passed.
- Deployment pending: restart only `marketcore-ui-shell.service`, then verify
  HTTP actions and visible state. Real execution remains disabled.

## V5 Edge Control UI runtime verified 22:15–22:17 МСК

- UI PID `3955695`; HTTP document quality `VERIFIED`.
- Exactly two normal-state commands: manual governed RUN and REFRESH.
- Autonomous mode: enabled; no-click operation continues independently.
- No broker, real-trading, micro-live or live-promotion commands rendered.
- Observed freshness: M1 226 sec (above 180-sec target), M5 346 sec (within
  420-sec threshold). Next checkpoint: independent fast V5 refresh subcycle.
- Verdict: `V5_EDGE_CONTROL_UI_ACTIVE_AUTONOMOUS_MODE`.

## V5 fast bars refresh prepared 22:18–22:23 МСК

- Independent exact-target fast refresh prepared for five M1 and two M5 V5 series.
- One-shot timer cadence: 60 sec after service completion; no self-overlap.
- Per-target timeout 15 sec; full unit timeout 120 sec; no execution commands.
- Validation: 7 tests plus systemd unit verification passed.
- Deployment pending: install/enable timer, then observe at least two cycles and
  require M1 age <=120 sec under normal vendor response.

## V5 fast bars runtime verified 22:34–22:36 МСК

- Timer enabled and active; two consecutive automatic cycles completed 7/7.
- No retry, no self-overlap, first observed duration about 9 sec.
- Freshness after cycle 2: M1=120 sec, M5=360 sec.
- Previous M1 age 226 sec is eliminated; target contract is satisfied.
- Verdict: `V5_FAST_BARS_REFRESH_RUNTIME_VERIFIED`.

## V5 hierarchical evidence prepared 22:38–22:47 МСК

- Four levels implemented with physical scope/timeframe isolation.
- Only clean V5 confirmed trades are consumed; V3/V4 never enter the router.
- OOS remains exact-only with 80 trades, PF/expectancy/cost gates.
- Scheduler executor and button-free Control Center hierarchy summary added.
- Validation: 17 focused tests passed.
- Pending: migration 215 + first router run + UI reload and runtime verification.

## V5 hierarchical evidence runtime verified 22:45–22:51 МСК

- Migration applied; 18 V5 groups built across 4 hierarchy levels.
- Current decisions: DISCOVERY_ONLY=18, EARLY_STOP=0, READY_FOR_OOS=0.
- Canonical timeframe lineage fixed: BR/NG=M1, equities=M5; LIVE/UNKNOWN=0.
- UI hierarchy verified without extra controls; nearest exact BRQ6=4/80.
- 13 focused tests and repeated router run passed.
- Verdict: `V5_HIERARCHICAL_EVIDENCE_RUNTIME_VERIFIED`.

## Accumulation snapshot 29.07.2026, 06:12 МСК

- Runtime units: all five research/Paper/UI services and timer active.
- Safety unchanged: Paper only; execution and real trading disabled; trailing
  order path remains dry-run.
- Clean `FRESH_V5_CONFIRM`: 11 closed trades, net PnL
  `-0.24490380000000403`, last close 28.07.2026 23:13 МСК.
- Open isolated Paper positions: 6 (NVTK, NGQ6, BRQ6, VTBR, LKOH, GAZP).
- Evidence groups: Strategy 3, Instrument/Side 4, Compatible Context 6,
  Exact Context 7; max exact sample remains 4/20.
- Leading exact branch: BRQ6 M1 breakout long, off-main, range-normal,
  regime-invalidation; 4 trades, expectancy `-0.165429375`, PF `0`,
  `DISCOVERY_ONLY`.
- OOS-ready branches: 0. Continue autonomous accumulation; next evidence
  checkpoint is the first exact branch at 20 closed trades.
- UI quality `VERIFIED`, autonomous mode enabled. UI last-hour closed count is 0;
  this does not conflict with the total clean sample of 11.
- Overnight raw bar age is session-bound and is not by itself evidence of a
  failed refresh loop; all relevant units were active at the snapshot.
- Source revision: `08ef6b274be6521e78049d22bb223391db4c8a9c` on
  `codex/research-edge-v5`.

## Evidence-driven acceleration 29.07.2026

- Exact evidence priority bands implemented: 20–79, 10–19, 5–9, 3–4,
  then 1–2 observations; early-stopped branches receive negative priority.
- Supporting hierarchy cannot outrank exact evidence. Runtime priority view is
  physically restricted to clean `FRESH_V5_CONFIRM` / `EXACT_CONTEXT` rows.
- Migration 216 applied and router rebuilt. Current runtime order starts with
  BRQ6 4 trades / score 304, then NGQ6 2 / 102, NVTK and VTBR 1 / 101.
- Open-position diagnostics added without buttons. Verified current completed-bar
  ages: BRQ6 31 M1, NGQ6 25 M1, VTBR 11 M5, NVTK 3 M5; GAZP/LKOH wait for the
  first completed M5 bar after the recoverable opening-time fallback.
- Validation: 24 focused tests; source compile; DB router verdict OK; render-tree
  quality `VERIFIED`.
- Pending deployment step: operator restart of `marketcore-ui-shell.service`.
  No pipeline restart is required. Real execution remains disabled.
- UI reload audit: disabled RUN during an active autonomous job now carries the
  required `RESEARCH_COMMAND_ALREADY_ACTIVE` reason. State-dependent render is
  `VERIFIED`; one additional UI-only reload is required for this hotfix.
- UI-only reload completed at 06:29:01 MSK. HTTP document is `VERIFIED`, open
  position diagnostics are present, command surface remains RUN + REFRESH only,
  and no broker/live commands are exposed. Deployment is complete.
