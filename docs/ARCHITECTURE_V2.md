# FINAM_CORE — ARCHITECTURE FREEZE V2

## Статус

ARCHITECTURE_FREEZE_V2

Research Layer = Frozen  
Analytics Layer = Frozen  
Shadow Layer = Frozen  
Presentation Layer = Active Development  
Execution Layer = Disabled  

## Миссия

FINAM_CORE — исследовательская платформа для поиска, проверки, объяснения и наблюдения торговых преимуществ до допуска каких-либо решений к реальному исполнению.

## Активный эпик

MARKETCORE_OPERATOR_WORKSPACE_V1

Цель — создать рабочее место аналитика, где за 30 секунд видно:

- какие edge наиболее сильные;
- почему система так считает;
- что изменилось за день;
- какие кандидаты усиливаются или ослабевают;
- какие исследования требуют внимания;
- есть ли риски или ограничения;
- в каком состоянии система.

## Архитектурные слои

### Core Platform

Статус: Frozen.

Включает:

- core;
- storage;
- data;
- scheduler;
- configuration;
- logging;
- observability.

Core Platform не меняется ради UI.

### Research Platform

Статус: Frozen.

Включает:

- market data;
- feature store;
- research;
- discovery;
- Edge Score V2;
- explain;
- reconciliation;
- shadow observation;
- daily analytics.

Инварианты:

runtime_allowed=0  
execution_allowed=0  
micro_live_allowed=0  
orders_changed=0  
fills_changed=0  

### Presentation Platform

Статус: Active Development.

Включает:

- navigation;
- operator workspace;
- component library;
- i18n;
- dashboard framework;
- theme;
- accessibility;
- mobile.

## Целевая структура меню

Главная

Исследования:
- Фабрика Edge
- Лучший Edge
- Shadow-наблюдение
- Ежедневная аналитика

Рынок:
- Модель рынка
- Инструменты
- Рыночная вселенная

Портфель:
- Портфель
- Позиции
- Риск

Данные:
- Рыночные данные
- История
- Статистика

Система:
- Планировщик
- Журнал
- Настройки
- О системе

Инженерные страницы должны быть скрыты из основного меню.

## Presentation Architecture

Целевая цепочка:

Page
↓
Provider
↓
ViewModel
↓
Component
↓
Theme
↓
HTML

Запрещено:

- SQL в компонентах;
- бизнес-логика в HTML;
- прямой доступ UI к execution;
- пользовательские строки без i18n;
- уникальные HTML-страницы без компонентов.

## I18N

Любой текст, который может увидеть пользователь, должен проходить через слой локализации.

Исключения:

- SQL;
- логи;
- диагностические сообщения;
- внутренние идентификаторы;
- имена таблиц и технических колонок.

Пространства имен:

- navigation.*
- page.*
- button.*
- table.*
- column.*
- dashboard.*
- strategy.*
- status.*
- tooltip.*
- dialog.*
- message.*
- error.*
- system.*
- market.*
- research.*
- risk.*
- portfolio.*
- runtime.*

Стратегии, статусы, рекомендации и подписи таблиц также проходят через i18n.

## UI Safety

В Presentation Layer запрещены:

- send_order;
- place_order;
- cancel_order;
- execute_order;
- LiveExecution;
- PaperExecution;
- FinamClient;
- INSERT INTO orders;
- INSERT INTO fills;
- UPDATE execution;
- UPDATE runtime.

## Правило разработки

Каждая новая функция проходит цепочку:

Идея
↓
Архитектура
↓
Схема данных
↓
Provider
↓
ViewModel
↓
Component
↓
Dashboard
↓
Bash Test
↓
Checkpoint

## Активная дорожная карта

1. MARKETCORE_UI_MENU_CLEANUP_V1 — done
2. MARKETCORE_UI_BUTTONS_AND_ICONS_AUDIT_V1 — done
3. MARKETCORE_UI_I18N_ARCHITECTURE_V1 — next
4. MARKETCORE_UI_I18N_COMPLETION_V1
5. MARKETCORE_UI_INFORMATION_ARCHITECTURE_V1
6. MARKETCORE_COMPONENT_LIBRARY_V1
7. MARKETCORE_DASHBOARD_FRAMEWORK_V1
8. MARKETCORE_OPERATOR_HOME_V1

## Итог

FINAM_CORE перешел от стадии построения исследовательской системы к стадии развития аналитической платформы.

Research Platform is stable.  
Shadow Observation is stable.  
Execution is disabled.  
Operator Workspace is the active development frontier.
