# MARKETCORE RESEARCH EDGE V5 — CANONICAL MANIFEST

Статус: canonical baseline + verified candle-driven swing
База: `50951c2ce1f20d8065a55707394708191e1f5b68`
Ветка: `codex/research-edge-v5`

## Назначение

V5 — изолированный Research/Paper-контур накопления режимно совместимых
закрытых сделок с точной атрибуцией, учётом издержек и последующим OOS.
Он не является допуском к реальной торговле.

## Обязательные инварианты

1. `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0` и отсутствие обхода Risk Engine.
2. Только подтверждённый `CANDLE_REGIME_V3`; unknown/stale/incomplete — fail closed.
3. Симметричный directional gate; контртренд только по явной DB-политике.
4. Стратегия и portfolio scope разрешаются из DB, legacy-статистика не наследуется.
5. Вход покрывает комиссии, spread и slippage по свежему microstructure snapshot.
6. Paper positions физически изолированы; restart не сбрасывает lifecycle/hold time.
7. Закрытие имеет exact signal/fill/context lineage.
8. Clean V5 view не смешивается с audit/excluded сделками.
9. OOS только после 80 сделок точной связки; Paper-накопление не равно edge verdict.

## Состав baseline

- Runtime: `paper_pipeline`, entry/runtime gates, regime/policy, cost gates,
  position lifecycle/projection, instrument specs и Paper fill metadata/materializer.
- DB: подтверждённая V5 cohort, cost admission, runtime scope/promotion policy,
  regime strategy assignments и физическая Paper isolation.
- UI: компактный source-backed V5 Control с clean/excluded/open состояниями.
- Tests: V5 regime, direction, costs, scope, lifecycle restore, materializer и UI source.

Точный список файлов фиксируется самим git commit; runtime/generated/log/backup
артефакты в baseline не входят.

## Проверенные продолжения baseline

- `d8e37ff6` — master-context verifier и исключение локальных runtime-артефактов.
- `3def889f` — полный PostgreSQL contract централизованного portfolio risk.
- `1b781d7c` — отдельный swing research/Paper-контур по закрытым H1/H4/D1-барам.
- `810cb2cb` — корректный приоритет явных adaptive entry constraints над profile defaults.

Непроверенный UI/OOS/runtime WIP изолирован на
`codex/quarantine-pre-v5-wip-20260728` (`f91941a7`) и в V5 не входит.

## Проверка кандидата

- AST parsing всех изменённых/новых Python-файлов: OK (173 файлов).
- V5 manifest contract suite в изолированном checkout индекса: 61 passed.
- Full dirty-tree suite не является acceptance gate manifest: legacy/WIP слой имеет
  45 падений и описан в `UNCOMMITTED_AUDIT_V5.md`.

VERDICT=V5_CANONICAL_MANIFEST_DEFINED
VERDICT=V5_CANONICAL_INDEX_VERIFIED
