# UNCOMMITTED AUDIT — RESEARCH EDGE V5

Дата аудита: 28.07.2026
Базовый commit: `50951c2ce1f20d8065a55707394708191e1f5b68`
Рабочая ветка: `codex/research-edge-v5`
Режим: Research / isolated Paper; real execution disabled

## Масштаб рабочего дерева

- 104 изменённых отслеживаемых файла: `+5828/-767`.
- Более 80 новых файлов.
- Изменения объединяют несколько поколений SQL (V2–V5), Paper runtime,
  risk, research/OOS, ingestion и UI.

## Не включать в эталон

- `.codex-backup/`, `.codex-tmp/`;
- `runtime/locks/`, `runtime/marketcore-ui-8080.log`;
- `data/snapshot.json` и generated runtime snapshots;
- локальные backup/runtime artifacts.

Эти объекты не удалены: аудит не выполняет разрушительных действий.

## Подтверждённый V5-контур

- подтверждённый candle regime и DB-driven strategy policy;
- symmetric direction gate, fail-closed;
- equity/futures entry cost gates по свежему стакану;
- V5 portfolio scope bootstrap без наследования старой статистики;
- изолированная Paper position projection/lifecycle;
- closed-trade materialization с режимом и стороной входа;
- чистая `closed_trades_fresh_v5_confirmed` отдельно от исключённых фактов;
- сохранение фактического времени открытия позиции после restart;
- Operator Control показывает clean/excluded/open Paper раздельно.

Проверки: AST parse 173 Python-файлов — OK; V5 contract suite — 61 passed.

## Блокеры эталонного commit

- Полный suite: 45 failures в смешанных legacy/WIP-контурах.
- Один тест не собирается: в серверном venv отсутствует объявленная зависимость
  `websockets==15.0.1`.
- Основные классы падений: устаревшие V4/V2 source assertions, UI contract drift,
  legacy ожидание `RiskEngine.evaluate() is None`, DB-state-dependent scout tests,
  calendar/OOS lineage и старые pipeline fixtures.

## Решение аудита

Текущее дерево не является эталоном и не должно коммититься целиком.
Ветка `codex/research-edge-v5` создана как изолированная точка сборки.
Эталонный commit допустим после разделения V5 manifest от legacy/WIP и зелёной
проверки всех файлов, входящих в manifest.

VERDICT=V5_CORE_VERIFIED_FULL_TREE_NOT_CANONICAL
