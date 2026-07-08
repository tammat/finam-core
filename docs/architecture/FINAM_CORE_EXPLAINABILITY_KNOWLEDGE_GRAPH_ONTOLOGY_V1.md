# MARKETCORE_EXPLAINABILITY_KNOWLEDGE_GRAPH_ONTOLOGY_V1

## 1. Назначение

Документ фиксирует онтологию Explainability Knowledge Graph для Finam_Core.

Цель графа знаний: объяснять торговые решения системы на основании фактов, контекстов, решений Runtime, Risk Engine, Edge Gate, исполнения и результата сделки.

## 2. Принципы LOCK

1. Knowledge Graph хранит факты, связи и доказательства, а не произвольные пересчёты.
2. Центральная сущность V1: Trade Context Snapshot.
3. Каждый узел должен иметь источник происхождения.
4. Каждая связь должна быть воспроизводима из PostgreSQL.
5. Explainability является частью графа, а не внешним текстовым комментарием.
6. UI не строит граф напрямую. UI читает только подготовленный слой.
7. PostgreSQL only.
8. Никакого SQLite.
9. Граф не отправляет ордера.
10. AI/LLM слой может объяснять и анализировать, но не может исполнять сделки.

## 3. Ядро онтологии V1

Базовые сущности:

- Signal
- Decision
- EdgeDecision
- RiskDecision
- RuntimeDecision
- FeatureContext
- RiskContext
- EdgeGate
- Execution
- Fill
- Trade
- Outcome
- Explanation
- Evidence

## 4. Центральный объект V1

Основная таблица-источник:

public.trade_context_snapshots

Причина выбора:

snapshots=4232
snapshots_with_signal_id=3543
snapshots_with_fill_id=923
snapshots_with_payload_trade_id=3639
linked_fills=923
linked_signal_fills=635
linked_signals=74
linked_signal_quality=74

closed_trades в V1 не является опорной таблицей KG, потому что прямые связи по signal_id и payload-связям недостаточны.

## 5. Основной путь объяснения

Trade Context Snapshot
    -> Attribution
    -> Edge Gate
    -> Risk Context
    -> Feature Context
    -> Exit Policy Context
    -> Execution
    -> Fill
    -> Outcome
    -> Explanation

## 6. Типы узлов

TradeContextSnapshot — центральный снимок решения/сделки. Источник: trade_context_snapshots.
Attribution — происхождение действия. Источник: snapshot.attribution.
Signal — торговый сигнал. Источник: snapshot.attribution.signal_id.
EdgeGate — решение edge gate. Источник: snapshot.attribution.trade_context_snapshot.edge_gate.
RiskContext — контекст риска. Источник: snapshot.risk_context.
FeatureContext — рыночные признаки. Источник: snapshot.feature_context.
ExitPolicyContext — контекст выхода. Источник: snapshot.exit_policy_context.
Fill — исполнение. Источник: fills / snapshot.attribution.fill_id.
Outcome — результат. Источник: closed_trades / derived later.
Explanation — человеческое объяснение. Источник: runtime_governance_live_accumulation_v1.raw_json.explainability.

## 7. Типы связей

HAS_ATTRIBUTION: TradeContextSnapshot -> Attribution.
HAS_SIGNAL: Attribution -> Signal.
HAS_EDGE_GATE: Attribution -> EdgeGate.
HAS_RISK_CONTEXT: TradeContextSnapshot -> RiskContext.
HAS_FEATURE_CONTEXT: TradeContextSnapshot -> FeatureContext.
HAS_EXIT_POLICY: TradeContextSnapshot -> ExitPolicyContext.
PRODUCED_FILL: Attribution -> Fill.
HAS_OUTCOME: TradeContextSnapshot -> Outcome.
EXPLAINED_BY: Decision/Outcome -> Explanation.
SUPPORTED_BY: Explanation -> Evidence.

## 8. Обязательные свойства узла

node_id
node_type
source_table
source_pk
source_path
symbol
strategy
timeframe
trade_source
ts
payload
created_at
ontology_version

## 9. Обязательные свойства связи

edge_id
from_node_id
to_node_id
edge_type
source_table
source_pk
confidence
created_at
ontology_version

## 10. Provenance

Каждый узел и каждая связь должны быть прослеживаемы до PostgreSQL-источника.

Запрещено создавать KG-узлы без источника.

## 11. Confidence

FULL — связь подтверждена прямым ключом.
PARTIAL — связь восстановлена из snapshot/payload.
WEAK — связь восстановлена по времени/символу/стратегии.
UNKNOWN — связь не используется в V1.

В V1 разрешены только FULL и PARTIAL.

## 12. Что не входит в KG V1

В V1 не включаем:

- OHLC bars;
- полные market_bars;
- технические логи systemd;
- временные UI-агрегаты;
- произвольные LLM-выводы без provenance;
- production execution без отдельного EPIC.

## 13. V1 Scope

V1 строится только по Paper Runtime.

Production, Shadow и Cross-Asset KG переносятся в следующие версии.

## 14. Roadmap

V1  Paper Explainability Graph
V2  Runtime Decision Graph
V3  Edge Validation Graph
V4  Portfolio Graph
V5  Cross-Asset / Cross-Strategy Graph
V6  Self-Learning Graph

## 15. Принятое решение

Для PAPER_RUNTIME_EXPLAINABILITY_GRAPH_STORAGE_V1 использовать trade_context_snapshots как центральный источник.

Storage должен материализовать существующие знания, а не пересчитывать торговую логику.
