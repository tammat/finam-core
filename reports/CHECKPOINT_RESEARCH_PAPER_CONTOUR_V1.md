# CHECKPOINT_RESEARCH_PAPER_CONTOUR_V1

Дата: 28.07.2026, МСК
Git branch: codex/research-edge-v5
Verified code HEAD: 810cb2cb96fb24e158520cdac19fc9a395fe00c0
Статус: V5_CANONICAL_CLEAN_INTRADAY_AND_SWING_VERIFIED

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
