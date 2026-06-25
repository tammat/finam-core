# ADR-001

## Название

Research Platform использует Event-Driven Architecture.

## Статус

APPROVED

## Дата

2026-06-25

## Основание

Во время проектирования Research Platform было выявлено архитектурное несоответствие.

Trading Core построен на Event-Driven Architecture.

Research Platform первоначально проектировалась как последовательный procedural pipeline.

Использование различных архитектур внутри одной системы увеличивает сложность сопровождения, усложняет расширение и нарушает единый архитектурный стиль проекта.

## Решение

Research Platform принимает ту же Event-Driven Architecture, что и Trading Core.

Каждый этап обработки публикует событие.

Последующие компоненты подписываются на соответствующие события.

Пример последовательности:

Market Features
↓
FeatureValidatedEvent
↓
FeatureNormalizedEvent
↓
ClassifierCompletedEvent
↓
ConflictResolvedEvent
↓
MarketStateBuiltEvent
↓
SignatureBuiltEvent

После публикации MarketStateBuiltEvent становятся возможны независимые подписчики:

- Edge Discovery Engine
- Strategy Recommendation Engine
- Dashboard
- Replay
- Telemetry
- AI Research (в будущем)

При этом сам MarketStateEngine не знает о существовании подписчиков.

## Последствия

Положительные

- единая архитектура Finam_Core;
- слабая связанность компонентов;
- простое масштабирование;
- простое добавление новых исследовательских модулей;
- соответствие существующей архитектуре Trading Core.

Отрицательные

- немного более сложная реализация Event Bus;
- необходимость дисциплины при определении событий.

## Ограничения

ADR не изменяет Конституцию проекта.

ADR не изменяет Runtime.

ADR не изменяет Execution.

ADR не включает реальную торговлю.

## Связанные checkpoint

checkpoint_market_state_engine_architecture_review_v1

checkpoint_market_state_engine_framework_plan_v1

checkpoint_market_state_engine_implementation_plan_v1

