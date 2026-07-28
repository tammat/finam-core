# CHECKPOINT_RESEARCH_PAPER_CONTOUR_V1

Дата: 28.07.2026, МСК
Git branch: feature/exit-alpha-v1
Git HEAD: 50951c2ce1f20d8065a55707394708191e1f5b68
Статус: V5_MONOTONIC_VIRTUAL_STOP_AWAITING_RELOAD

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

- Ветка: `codex/research-edge-v5`.
- 104 modified tracked files, `+5828/-767`, более 80 untracked.
- AST: 173 Python files OK.
- Full suite: 45 failures; один collection blocker из-за отсутствующего `websockets` в venv.
- Runtime snapshots, logs, locks и backup-каталоги исключены из будущего manifest.
- Эталонный commit ещё не создан: известные регрессии нельзя закреплять как baseline.

## Canonical manifest

- Явный staged manifest: 95 файлов, без snapshots/logs/locks/backups и UI/legacy WIP.
- Проверен отдельный checkout содержимого git index: `61 passed`.
- Safety diff: execution/real execution только отключены; секреты не обнаружены.
- Готов к созданию эталонного V5 commit.

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
