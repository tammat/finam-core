# MARKETCORE OS INFORMATION ARCHITECTURE V1

Версия: 1.0

Статус: Architecture Freeze

Дата: 2026-07-02

---

# Назначение

Документ определяет информационную архитектуру MarketCore OS.

Все новые страницы, сервисы и виджеты должны соответствовать данной архитектуре.

---

# Основной принцип

Пользователь никогда не ищет информацию.

Информация сама показывает пользователю:

- текущее состояние;
- проблему;
- следующее рекомендуемое действие.

---

# Первый уровень навигации

☰ Главное меню

1. Home
2. Capital
3. Edge
4. Research
5. Intraday
6. Portfolio
7. Risk
8. Program
9. Settings

Максимум 9 пунктов.

Новые разделы первого уровня запрещены без изменения настоящего документа.

---

# HOME

Назначение

Рабочее место пользователя.

Отвечает на вопросы:

- Что происходит?
- Что изменилось?
- Что делать сейчас?

Виджеты:

- Capital Summary
- Working Edge
- Program Board
- Risk Status
- Next Action
- Alerts

---

# CAPITAL

Назначение

Управление капиталом.

Разделы:

- Capital Summary
- Allocation
- Capital History
- Performance
- Currency
- FX

---

# EDGE

Назначение

Жизненный цикл торговых преимуществ.

Разделы:

- Production Edge
- Paper Edge
- Shadow Edge
- Research Candidate
- Archived Edge

---

# RESEARCH

Назначение

Полный конвейер исследований.

Pipeline:

Ideas

↓

Replay

↓

Ranking

↓

Forensic

↓

Robustness

↓

Walk Forward

↓

OOS

↓

Candidate

↓

Shadow

↓

Paper

↓

Production

---

# INTRADAY

Назначение

Тактическая внутридневная торговля.

Разделы:

- Daily Scanner
- Setup Library
- Trade Plan
- Active Trades
- Journal
- Statistics

---

# PORTFOLIO

Назначение

Управление портфелем Edge.

Разделы:

- Working Edge
- Allocation
- Correlation
- Capacity
- Diversification

---

# RISK

Назначение

Контроль риска.

Разделы:

- Runtime Risk
- Daily Risk
- Drawdown
- Kill Switch
- Events
- Limits

---

# PROGRAM

Назначение

Управление развитием проекта.

Разделы:

- Quarter Goal
- KPI
- Program Board
- Active Epic
- Completed Epic
- Roadmap

---

# SETTINGS

Назначение

Настройки пользователя.

Разделы:

- Language
- Timezone
- Currency
- Theme
- Workspace
- Notifications

---

# Второй уровень

Каждый раздел первого уровня имеет собственное меню.

Максимум:

7 страниц.

---

# Карточки

Каждая карточка отвечает только на один вопрос.

Название слева.

Значение справа.

Статус справа.

---

# Виджеты

Все страницы собираются исключительно из Widget.

Widget независим.

Widget может использоваться на нескольких страницах.

---

# API

UI

↓

REST API

↓

Services

↓

PostgreSQL

Прямой доступ UI к PostgreSQL запрещён.

---

# Мобильная версия

Полностью повторяет Desktop.

Различается только расположением элементов.

Функциональность идентична.

---

# Главное правило

Каждый экран обязан помогать принять решение.

Если экран не помогает принять решение:

по капиталу;

по Edge;

по риску;

по исследованиям;

по внутридневной торговле;

то экран не включается в MarketCore OS.

---

# Roadmap

V1

Основной интерфейс.

V2

Workspace.

V3

Knowledge.

V4

AI Explain.

V5

Adaptive Capital Manager.
