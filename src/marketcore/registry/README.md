# REGISTRY_FRAMEWORK_V1

Назначение: единый внутренний SDK для новых Registry MarketCore.

## Правила

1. Framework не хранит данные.
2. Framework не является ORM.
3. Новые Registry обязаны использовать этот Framework.
4. Существующие Registry не переписываются массово.
5. Существующие Registry переходят на Framework только при следующей доработке.
6. AI Registry становится первым Registry второго поколения.

## Стандартный вертикальный срез Registry

schema → builder → validation → cli → read_only_ui → complete → checkpoint

## Запреты

- Не создавать второй источник истины.
- Не дублировать Feature/Model/Experiment в AI Registry.
- Не добавлять runtime/execution side effects.
- Не использовать SQLite.
