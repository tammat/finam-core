# EDGE FACTORY ROADMAP

## 1. Mission

Finam_Core больше не рассматривается как проект по написанию торгового робота.

Finam_Core — это фабрика поиска, проверки и сопровождения статистически устойчивых торговых преимуществ.

Главная цель:

Найти, проверить и довести до Paper / Shadow / Live такие edge, которые имеют положительное ожидание после комиссий, риска и смены рыночных режимов.

## 2. Core Principle

Architecture Stable. Algorithms Adaptive.

Архитектура заморожена.
Алгоритмы, параметры, стратегии, модели исполнения и политики отбора могут изменяться по результатам исследований.

Любое изменение должно отвечать хотя бы одному критерию:

- быстрее найти edge;
- лучше оценить edge;
- отбросить ложный edge;
- безопаснее довести edge до Paper;
- снизить риск;
- повысить Research Velocity.

## 3. Execution Pipeline

Market
→ Feature
→ Strategy
→ Edge
→ Risk
→ Trading
→ Portfolio

Исполнительный контур не переписывается без критической необходимости.

## 4. Research Pipeline

Strategy Library
→ Research Queue
→ Parameter Search
→ Execution Runner
→ Edge Observation
→ Edge Score
→ Discovery
→ Validation
→ Paper
→ Shadow
→ Micro Live
→ Live

Главная сущность Research Phase — Edge Observation.

Candidate создаётся только из Observation.

## 5. Edge Factory KPI

Основные KPI проекта:

- Research Queue size
- Observations total
- Observations with trades
- Edge Candidates
- Validated Candidates
- Paper Candidates
- Shadow Candidates
- Live Candidates
- Research trades
- Best Profit Factor
- Best Expectancy
- Best Edge Score
- Candidate conversion rate
- Paper conversion rate
- Research throughput per day

## 6. Current Operating Cycle

EDGE SPRINT
→ Review
→ Algorithm Improvement
→ New EDGE SPRINT

Каждый sprint должен давать измеримый результат:

- сколько гипотез проверено;
- сколько observation создано;
- сколько observation имеют сделки;
- сколько candidate найдено;
- сколько candidate прошло validation;
- какие стратегии, инструменты и параметры дали лучший результат.

## 7. Near Roadmap

1. DECISION_ENGINE_FOUNDATION_V1
2. ARCHITECTURE_FREEZE_V3
3. EDGE_SPRINT_1
4. EDGE_SPRINT_REVIEW_1
5. STRATEGY_IMPROVEMENT_1
6. PARAMETER_SEARCH_IMPROVEMENT_1
7. PAPER_RUNTIME_CANDIDATE_V1
8. PAPER_PORTFOLIO_MTM_V1
9. SHADOW_RUNTIME_V1

## 8. What We Do Not Do Now

Не строим новые платформы без прямой необходимости.

Не добавляем Registry, Dispatcher, Interface, если это не ускоряет поиск edge.

Не делаем косметический рефакторинг до появления устойчивых Paper-кандидатов.

Не включаем Micro Live / Live без отдельного governance-gate.

## 9. Safety Rule

AI layer cannot send orders directly.

Paper, Shadow, Micro Live и Live должны проходить через Risk и Governance.

micro_live_allowed по умолчанию false.

live_allowed по умолчанию false.

## 10. Definition of Result

Результат проекта — не наличие кода.

Результат проекта — воспроизводимый процесс:

Observation
→ Candidate
→ Validated
→ Paper
→ Shadow
→ Live

с положительным expectancy после комиссий и контролируемым риском.
