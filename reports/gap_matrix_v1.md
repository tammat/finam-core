# Finam_Core Gap Matrix v1

## Critical

| Gap | Why it matters | Next action |
|---|---|---|
| Strategy edge not proven | Runtime уже умеет BLOCK/WATCH, но alpha ещё слабая | Build Research Analytics Core v1 |
| Env/config sprawl | Много параметров ещё читается напрямую | Continue RuntimeConfig migration by priority |
| Runtime governance scattered | Governance logic spread across scripts/pipeline | Design RuntimeGovernanceLayer v1 |
| Paper/real execution parity not fully verified | Paper gate есть, real path надо сверить | Add real-execution dry-run override gate test |

## Important

| Gap | Why it matters | Next action |
|---|---|---|
| No Strategy Registry | Стратегии сложно учитывать централизованно | Add StrategyRegistry v1 |
| No unified health report | Сложно быстро понять состояние системы | Add system health report script |
| Feature Store partial | Часть feature context уже есть, но не централизована полностью | Extend feature_snapshots schema |
| Reports generated but not summarized | Есть raw audit, но нужна управленческая матрица | Maintain gap_matrix_v1.md |

## Later

| Gap | Why it matters | Next action |
|---|---|---|
| AI layer absent | Пока рано без устойчивой статистики | Add after Research Core |
| Adaptive sizing advanced logic | Нужна после доказанного edge | RuntimeGovernanceLayer v2 |
| Metals/yuan strategy logic | Данные есть, alpha нет | Add later after BR/NG/USD stabilized |
