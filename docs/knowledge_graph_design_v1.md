# KNOWLEDGE_GRAPH_DESIGN_V1

## Назначение

Knowledge Graph — единый слой связей MarketCore.

Цель: обеспечить трассировку от исходного объекта до runtime-использования.

## Узлы графа

- CATALOG_OBJECT
- FEATURE
- EXPERIMENT
- MODEL
- CANDIDATE
- PAPER_SESSION
- RUNTIME_SIGNAL
- TRADE
- RISK_EVENT
- REPORT

## Типы связей

- CATALOG_TO_FEATURE
- CATALOG_TO_MODEL
- FEATURE_TO_EXPERIMENT
- EXPERIMENT_TO_MODEL
- MODEL_TO_CANDIDATE
- CANDIDATE_TO_PAPER
- PAPER_TO_RUNTIME
- RUNTIME_TO_TRADE
- TRADE_TO_RISK_EVENT
- EXPERIMENT_TO_REPORT

## Правила

1. Граф строится только из проверенных Registry/Relationship-таблиц.
2. Граф не копирует исходные данные.
3. Каждый edge должен иметь source_of_truth, evidence_level, validation_status.
4. AI использует граф только для анализа и рекомендаций.
5. AI не изменяет runtime, orders, fills и execution.
6. Все новые связи проходят validation.
7. UI отображается только через ReadOnly UI на 8089.

## Первый минимальный граф V1

В V1 включаются только уже подтверждённые связи:

- CATALOG_TO_FEATURE = 352
- CATALOG_TO_MODEL = 280

## Следующее расширение

- FEATURE_TO_EXPERIMENT
- EXPERIMENT_TO_MODEL

## Политика безопасности

runtime_changed=0  
execution_changed=0  
orders_changed=0  
fills_changed=0  
micro_live_allowed=0
