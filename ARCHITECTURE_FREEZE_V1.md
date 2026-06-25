# FINAM CORE — ARCHITECTURE FREEZE V1

Версия: 1.0
Статус: APPROVED
Дата принятия: 25.06.2026

## 1. Цель

Фиксируется завершение архитектурного этапа Research Platform.

Дальнейший фокус проекта — поиск статистически подтвержденного Edge, а не расширение архитектуры.

## 2. Завершенные компоненты

- Event Engine
- PostgreSQL Storage Layer
- Research Layer
- Market State Engine
- Context Engine
- Trade Linking
- Historical Backfill
- Candidate Registry
- Research Knowledge Base
- Shadow Runtime
- Historical Scorecards
- Context Scorecards

## 3. Главная цель

Обнаружение статистически устойчивых торговых преимуществ, пригодных для перевода в Micro Live и Runtime.

## 4. Приоритеты

1. Качество данных.
2. Полнота исторических данных.
3. Корректность статистики.
4. Качество моделей.
5. Производительность.
6. Новый функционал.

## 5. Research First

Runtime не является источником знаний.
Research является источником принятия решений.
Runtime использует результаты Research.

## 6. Candidate Registry

Каждая найденная закономерность получает постоянный Candidate ID.

Жизненный цикл:

DISCOVERED
UNDER_RESEARCH
REJECTED
ARCHIVED
PROMOTED_TO_SHADOW
PROMOTED_TO_MICRO_LIVE
PROMOTED_TO_RUNTIME

Ни один кандидат не удаляется.

## 7. Research Knowledge Base

Все результаты исследований сохраняются.

Повторное исследование отклоненной гипотезы допускается только при наличии новых данных, новой методики, нового контекста или нового периода рынка.

## 8. Research Universe

После утверждения RESEARCH_UNIVERSE_V1 состав исследовательской вселенной считается базовым.

## 9. Архитектурные ограничения

Без отдельного архитектурного решения запрещается:

- создание новых уровней архитектуры;
- создание новых глобальных сущностей;
- изменение Event Architecture;
- изменение Knowledge Base;
- изменение Candidate Registry;
- изменение базовой модели Market State.

## 10. Разрешенные изменения

Допускаются:

- новые классификаторы внутри существующей архитектуры;
- новые источники данных;
- новые инструменты в рамках Research Universe;
- новые Context внутри существующей модели Context Engine;
- оптимизация производительности;
- повышение качества статистики;
- исправление ошибок.

## 11. Критерий готовности Edge

Edge допускается к следующему этапу только после цепочки:

Discovery
Candidate Registry
Knowledge Base
Robustness
Out-of-Sample
Forward Validation
Shadow
Micro Live
Runtime

## 12. Новая стадия проекта

DISCOVER STATISTICAL EDGE

## 13. Минимальная архитектурная достаточность

Любое изменение архитектуры должно отвечать на вопрос:

Невозможно ли достичь той же цели средствами уже существующей архитектуры?

Если возможно — новая архитектура не создается.
