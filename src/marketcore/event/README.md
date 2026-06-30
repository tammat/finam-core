# EVENT_FRAMEWORK_V1

Назначение: единый SDK событий MarketCore.

## Правила

1. Любая новая Event-таблица обязана использовать Event Framework.
2. Event неизменяем после публикации.
3. UPDATE событий запрещён архитектурно.
4. Исправление выполняется через Correction Event или новый normalization_run.
5. Event использует IDENTITY_POLICY_V1.
6. Event имеет две временные оси: event_time и received_at.
7. Time order policy: event_time <= source_time <= received_at <= normalized_at.
8. Quality не смешивается с Lifecycle.
9. Payload не заменяет нормальную схему таблицы.
10. AI читает только validated/research-ready события.

## Canonical Event Frame

- event_id
- event_uuid
- event_sequence
- event_type
- event_version
- source_system_id
- source_key
- normalization_run_id
- algorithm_version
- quality_status
- event_time
- source_time
- received_at
- normalized_at
- created_at
- payload

## Migration Policy

Новые Event строятся на Event Framework. Массовый рефакторинг запрещён.
