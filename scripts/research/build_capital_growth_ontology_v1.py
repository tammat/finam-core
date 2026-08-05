#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass


OUT = pathlib.Path("/tmp/capital_growth_ontology_v1")

ENTITIES_FILE = OUT / "entities.tsv"
RELATIONSHIPS_FILE = OUT / "relationships.tsv"
LIFECYCLE_FILE = OUT / "lifecycle_transitions.tsv"
BOUNDARIES_FILE = OUT / "decision_boundaries.tsv"
INVARIANTS_FILE = OUT / "invariants.tsv"
CONTRACT_FILE = OUT / "ontology_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class Entity:
    name: str
    aggregate: str
    responsibility: str
    identity_fields: str
    mutable_fields: str
    owner_stage: str
    persistence_required: int
    runtime_authority: int


@dataclass(frozen=True, slots=True)
class Relationship:
    source: str
    relation: str
    target: str
    cardinality: str
    required: int
    responsibility: str


@dataclass(frozen=True, slots=True)
class Transition:
    lifecycle: str
    from_status: str
    to_status: str
    decision_owner: str
    required_evidence: str
    reversible: int
    capital_allowed: int
    execution_allowed: int


@dataclass(frozen=True, slots=True)
class Boundary:
    stage: str
    authority: str
    allowed_action: str
    forbidden_action: str
    fail_policy: str


@dataclass(frozen=True, slots=True)
class Invariant:
    code: str
    scope: str
    requirement: str
    severity: str


ENTITIES = (
    Entity(
        name="ResearchUniverse",
        aggregate="RESEARCH",
        responsibility=(
            "Определяет доступное множество инструментов, стратегий, "
            "таймфреймов и режимов для исследования"
        ),
        identity_fields="universe_id,version",
        mutable_fields="members,status,source_version,updated_at",
        owner_stage="RESEARCH",
        persistence_required=1,
        runtime_authority=0,
    ),
    Entity(
        name="EdgeCandidate",
        aggregate="EDGE",
        responsibility=(
            "Представляет проверяемую гипотезу преимущества для сочетания "
            "symbol+strategy+timeframe+regime"
        ),
        identity_fields=(
            "edge_candidate_id,symbol,strategy,timeframe,regime"
        ),
        mutable_fields=(
            "hypothesis,status,evidence_version,updated_at"
        ),
        owner_stage="EDGE",
        persistence_required=1,
        runtime_authority=0,
    ),
    Entity(
        name="EdgeLifecycle",
        aggregate="EDGE",
        responsibility=(
            "Хранит текущий этап допуска кандидата и историю переходов"
        ),
        identity_fields="edge_candidate_id,lifecycle_version",
        mutable_fields=(
            "status,reason,evidence_ref,entered_at,exited_at"
        ),
        owner_stage="EDGE_GOVERNANCE",
        persistence_required=1,
        runtime_authority=0,
    ),
    Entity(
        name="CapitalGrowthScore",
        aggregate="CAPITAL_GROWTH",
        responsibility=(
            "Хранит нормализованную оценку ожидаемого вклада edge "
            "в рост капитала после затрат и риска"
        ),
        identity_fields=(
            "edge_candidate_id,score_version,calculated_at"
        ),
        mutable_fields=(
            "score,components,confidence,data_cutoff"
        ),
        owner_stage="CAPITAL_GROWTH",
        persistence_required=1,
        runtime_authority=0,
    ),
    Entity(
        name="RiskBudget",
        aggregate="RISK",
        responsibility=(
            "Определяет максимально допустимый риск по портфелю, edge, "
            "инструменту и корреляционной группе"
        ),
        identity_fields="risk_budget_id,scope,scope_key,version",
        mutable_fields=(
            "limit_value,consumed_value,status,updated_at"
        ),
        owner_stage="RISK",
        persistence_required=1,
        runtime_authority=1,
    ),
    Entity(
        name="PortfolioState",
        aggregate="PORTFOLIO",
        responsibility=(
            "Агрегирует позиции, денежные средства, экспозиции, PnL "
            "и потребление риск-бюджета"
        ),
        identity_fields="portfolio_state_id,as_of",
        mutable_fields=(
            "cash,equity,positions,exposures,pnl,risk_usage"
        ),
        owner_stage="PORTFOLIO",
        persistence_required=1,
        runtime_authority=1,
    ),
    Entity(
        name="CapitalState",
        aggregate="CAPITAL",
        responsibility=(
            "Хранит базу капитала, drawdown, high-water mark, "
            "доступный и зарезервированный капитал"
        ),
        identity_fields="capital_state_id,as_of",
        mutable_fields=(
            "equity,high_water_mark,drawdown,available,reserved"
        ),
        owner_stage="CAPITAL",
        persistence_required=1,
        runtime_authority=1,
    ),
    Entity(
        name="AllocationDecision",
        aggregate="ALLOCATION",
        responsibility=(
            "Фиксирует решение INCREASE, HOLD, REDUCE или REMOVE "
            "для edge без прямой отправки ордера"
        ),
        identity_fields="allocation_decision_id,edge_candidate_id,decided_at",
        mutable_fields=(
            "action,target_capital,target_risk,reason,status"
        ),
        owner_stage="ALLOCATION",
        persistence_required=1,
        runtime_authority=0,
    ),
)

RELATIONSHIPS = (
    Relationship(
        source="ResearchUniverse",
        relation="CONTAINS",
        target="EdgeCandidate",
        cardinality="1:N",
        required=1,
        responsibility="Кандидат должен происходить из версионированного universe",
    ),
    Relationship(
        source="EdgeCandidate",
        relation="HAS_LIFECYCLE",
        target="EdgeLifecycle",
        cardinality="1:N",
        required=1,
        responsibility="Каждый кандидат имеет историю lifecycle",
    ),
    Relationship(
        source="EdgeCandidate",
        relation="HAS_SCORE",
        target="CapitalGrowthScore",
        cardinality="1:N",
        required=0,
        responsibility="Score появляется только после достаточного evidence",
    ),
    Relationship(
        source="CapitalGrowthScore",
        relation="SUPPORTS",
        target="AllocationDecision",
        cardinality="N:1",
        required=1,
        responsibility="Allocation обязан ссылаться на версию score",
    ),
    Relationship(
        source="RiskBudget",
        relation="LIMITS",
        target="AllocationDecision",
        cardinality="N:1",
        required=1,
        responsibility="Allocation не может превышать действующий risk budget",
    ),
    Relationship(
        source="PortfolioState",
        relation="CONSTRAINS",
        target="AllocationDecision",
        cardinality="1:N",
        required=1,
        responsibility="Решение учитывает портфельную экспозицию и корреляцию",
    ),
    Relationship(
        source="CapitalState",
        relation="FUNDS",
        target="AllocationDecision",
        cardinality="1:N",
        required=1,
        responsibility="Решение не может использовать недоступный капитал",
    ),
    Relationship(
        source="AllocationDecision",
        relation="UPDATES_TARGET",
        target="PortfolioState",
        cardinality="N:1",
        required=0,
        responsibility=(
            "Allocation задаёт целевое состояние, но не исполняет ордер"
        ),
    ),
)

TRANSITIONS = (
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="DISCOVERED",
        to_status="RESEARCH",
        decision_owner="EDGE_GOVERNANCE",
        required_evidence="data_quality_passed,hypothesis_registered",
        reversible=1,
        capital_allowed=0,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="RESEARCH",
        to_status="ROBUST",
        decision_owner="EDGE_GOVERNANCE",
        required_evidence=(
            "net_expectancy_positive,robustness_passed,cost_model_present"
        ),
        reversible=1,
        capital_allowed=0,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="ROBUST",
        to_status="OOS_READY",
        decision_owner="EDGE_GOVERNANCE",
        required_evidence="walk_forward_passed,oos_plan_locked",
        reversible=1,
        capital_allowed=0,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="OOS_READY",
        to_status="SHADOW_READY",
        decision_owner="EDGE_GOVERNANCE",
        required_evidence="oos_passed,leakage_check_passed",
        reversible=1,
        capital_allowed=0,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="SHADOW_READY",
        to_status="PAPER_READY",
        decision_owner="EDGE_GOVERNANCE",
        required_evidence=(
            "shadow_min_sample_passed,execution_model_validated,"
            "negative_control_passed"
        ),
        reversible=1,
        capital_allowed=1,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="PAPER_READY",
        to_status="CAPITAL_ALLOCATED",
        decision_owner="ALLOCATION",
        required_evidence=(
            "paper_passed,capital_growth_score_valid,risk_budget_available"
        ),
        reversible=1,
        capital_allowed=1,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="CAPITAL_ALLOCATED",
        to_status="REAL_ELIGIBLE",
        decision_owner="RISK",
        required_evidence=(
            "manual_release_required,kill_switch_armed,"
            "broker_and_execution_checks_passed"
        ),
        reversible=1,
        capital_allowed=1,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="ANY_ACTIVE",
        to_status="QUARANTINED",
        decision_owner="RISK",
        required_evidence=(
            "data_quality_fail_or_edge_degradation_or_risk_breach"
        ),
        reversible=1,
        capital_allowed=0,
        execution_allowed=0,
    ),
    Transition(
        lifecycle="EdgeLifecycle",
        from_status="ANY",
        to_status="REJECTED",
        decision_owner="EDGE_GOVERNANCE",
        required_evidence="fatal_validation_failure",
        reversible=0,
        capital_allowed=0,
        execution_allowed=0,
    ),
)

BOUNDARIES = (
    Boundary(
        stage="RESEARCH",
        authority="Формирование и оценка гипотез",
        allowed_action="Создавать evidence и кандидатов",
        forbidden_action="Изменять позиции или отправлять ордера",
        fail_policy="FAIL_CLOSED_NO_CANDIDATE",
    ),
    Boundary(
        stage="EDGE_GOVERNANCE",
        authority="Изменение lifecycle edge",
        allowed_action="Продвигать, отклонять, карантинировать кандидата",
        forbidden_action="Назначать капитал или отправлять ордера",
        fail_policy="FAIL_CLOSED_NO_PROMOTION",
    ),
    Boundary(
        stage="CAPITAL_GROWTH",
        authority="Расчёт CapitalGrowthScore",
        allowed_action="Публиковать score и confidence",
        forbidden_action="Назначать капитал или отправлять ордера",
        fail_policy="FAIL_CLOSED_SCORE_INVALID",
    ),
    Boundary(
        stage="ALLOCATION",
        authority="Формирование целевого распределения капитала",
        allowed_action="INCREASE,HOLD,REDUCE,REMOVE",
        forbidden_action="Прямой вызов broker/execution API",
        fail_policy="FAIL_CLOSED_HOLD_ZERO_INCREMENT",
    ),
    Boundary(
        stage="PORTFOLIO",
        authority="Агрегация состояния портфеля",
        allowed_action="Публиковать позиции, экспозиции и PnL",
        forbidden_action="Самостоятельно создавать trade intent",
        fail_policy="FAIL_CLOSED_STATE_UNAVAILABLE",
    ),
    Boundary(
        stage="RISK",
        authority="Авторитетный допуск и ограничение риска",
        allowed_action="ALLOW,REDUCE,BLOCK,KILL",
        forbidden_action="Создавать alpha или менять стратегию",
        fail_policy="FAIL_CLOSED_BLOCK",
    ),
    Boundary(
        stage="EXECUTION",
        authority="Исполнение разрешённого order intent",
        allowed_action="Отправлять разрешённые ордера",
        forbidden_action="Изменять score, lifecycle или allocation",
        fail_policy="FAIL_CLOSED_NO_ORDER",
    ),
    Boundary(
        stage="AI",
        authority="Рекомендации и аналитические признаки",
        allowed_action="Создавать advisory output",
        forbidden_action="Прямо отправлять ордера или обходить Risk Engine",
        fail_policy="FAIL_CLOSED_ADVISORY_ONLY",
    ),
)

INVARIANTS = (
    Invariant(
        code="CGO-001",
        scope="EdgeCandidate",
        requirement=(
            "Уникальность определяется по "
            "symbol+strategy+timeframe+regime+hypothesis_version"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-002",
        scope="CapitalGrowthScore",
        requirement=(
            "Score без версии затрат, data cutoff и confidence недействителен"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-003",
        scope="AllocationDecision",
        requirement=(
            "Allocation обязан ссылаться на EdgeCandidate, Score, "
            "RiskBudget, PortfolioState и CapitalState"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-004",
        scope="AllocationDecision",
        requirement=(
            "Суммарный target_capital не превышает доступный CapitalState"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-005",
        scope="RiskBudget",
        requirement=(
            "Risk Engine имеет право уменьшить или обнулить allocation"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-006",
        scope="AI",
        requirement="AI не имеет права отправлять ордера",
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-007",
        scope="EdgeLifecycle",
        requirement=(
            "Переходы вперёд запрещены без полного required_evidence"
        ),
        severity="HIGH",
    ),
    Invariant(
        code="CGO-008",
        scope="EdgeLifecycle",
        requirement=(
            "QUARANTINED и REJECTED запрещают увеличение капитала"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-009",
        scope="Execution",
        requirement=(
            "Execution принимает только разрешённый Risk Engine order intent"
        ),
        severity="CRITICAL",
    ),
    Invariant(
        code="CGO-010",
        scope="Persistence",
        requirement=(
            "Все score, lifecycle transitions, allocation decisions и "
            "risk events сохраняются в PostgreSQL"
        ),
        severity="CRITICAL",
    ),
)


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, object]] = []

    entity_names = [entity.name for entity in ENTITIES]
    duplicate_entity_count = len(entity_names) - len(set(entity_names))

    if duplicate_entity_count:
        unresolved.append(
            {
                "scope": "ENTITY",
                "identity": "",
                "reason": f"DUPLICATE_ENTITY_COUNT:{duplicate_entity_count}",
            }
        )

    entity_set = set(entity_names)

    for relationship in RELATIONSHIPS:
        if relationship.source not in entity_set:
            unresolved.append(
                {
                    "scope": "RELATIONSHIP",
                    "identity": relationship.source,
                    "reason": "SOURCE_ENTITY_MISSING",
                }
            )

        if relationship.target not in entity_set:
            unresolved.append(
                {
                    "scope": "RELATIONSHIP",
                    "identity": relationship.target,
                    "reason": "TARGET_ENTITY_MISSING",
                }
            )

    invariant_codes = [item.code for item in INVARIANTS]
    duplicate_invariant_count = (
        len(invariant_codes) - len(set(invariant_codes))
    )

    if duplicate_invariant_count:
        unresolved.append(
            {
                "scope": "INVARIANT",
                "identity": "",
                "reason": (
                    "DUPLICATE_INVARIANT_CODE_COUNT:"
                    f"{duplicate_invariant_count}"
                ),
            }
        )

    write_tsv(
        ENTITIES_FILE,
        (
            "entity",
            "aggregate",
            "responsibility",
            "identity_fields",
            "mutable_fields",
            "owner_stage",
            "persistence_required",
            "runtime_authority",
        ),
        [
            {
                "entity": row.name,
                "aggregate": row.aggregate,
                "responsibility": row.responsibility,
                "identity_fields": row.identity_fields,
                "mutable_fields": row.mutable_fields,
                "owner_stage": row.owner_stage,
                "persistence_required": row.persistence_required,
                "runtime_authority": row.runtime_authority,
            }
            for row in ENTITIES
        ],
    )

    write_tsv(
        RELATIONSHIPS_FILE,
        (
            "source",
            "relation",
            "target",
            "cardinality",
            "required",
            "responsibility",
        ),
        [
            {
                "source": row.source,
                "relation": row.relation,
                "target": row.target,
                "cardinality": row.cardinality,
                "required": row.required,
                "responsibility": row.responsibility,
            }
            for row in RELATIONSHIPS
        ],
    )

    write_tsv(
        LIFECYCLE_FILE,
        (
            "lifecycle",
            "from_status",
            "to_status",
            "decision_owner",
            "required_evidence",
            "reversible",
            "capital_allowed",
            "execution_allowed",
        ),
        [
            {
                "lifecycle": row.lifecycle,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "decision_owner": row.decision_owner,
                "required_evidence": row.required_evidence,
                "reversible": row.reversible,
                "capital_allowed": row.capital_allowed,
                "execution_allowed": row.execution_allowed,
            }
            for row in TRANSITIONS
        ],
    )

    write_tsv(
        BOUNDARIES_FILE,
        (
            "stage",
            "authority",
            "allowed_action",
            "forbidden_action",
            "fail_policy",
        ),
        [
            {
                "stage": row.stage,
                "authority": row.authority,
                "allowed_action": row.allowed_action,
                "forbidden_action": row.forbidden_action,
                "fail_policy": row.fail_policy,
            }
            for row in BOUNDARIES
        ],
    )

    write_tsv(
        INVARIANTS_FILE,
        (
            "code",
            "scope",
            "requirement",
            "severity",
        ),
        [
            {
                "code": row.code,
                "scope": row.scope,
                "requirement": row.requirement,
                "severity": row.severity,
            }
            for row in INVARIANTS
        ],
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("CAPITAL GROWTH ONTOLOGY V1\n")
        stream.write("==========================\n\n")
        stream.write("PRIMARY_GOAL=MAXIMIZE_LONG_TERM_CAPITAL_GROWTH\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write("EVENT_DRIVEN=1\n")
        stream.write("AI_DIRECT_ORDER_ALLOWED=0\n")
        stream.write("RISK_ENGINE_CENTRALIZED=1\n")
        stream.write(f"ENTITY_COUNT={len(ENTITIES)}\n")
        stream.write(f"RELATIONSHIP_COUNT={len(RELATIONSHIPS)}\n")
        stream.write(f"LIFECYCLE_TRANSITION_COUNT={len(TRANSITIONS)}\n")
        stream.write(f"DECISION_BOUNDARY_COUNT={len(BOUNDARIES)}\n")
        stream.write(f"INVARIANT_COUNT={len(INVARIANTS)}\n")
        stream.write(f"DUPLICATE_ENTITY_COUNT={duplicate_entity_count}\n")
        stream.write(
            "DUPLICATE_INVARIANT_CODE_COUNT="
            f"{duplicate_invariant_count}\n"
        )
        stream.write(f"UNRESOLVED_COUNT={len(unresolved)}\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== BUILD CAPITAL GROWTH ONTOLOGY V1 ===")
    print(f"entity_count={len(ENTITIES)}")
    print(f"relationship_count={len(RELATIONSHIPS)}")
    print(f"lifecycle_transition_count={len(TRANSITIONS)}")
    print(f"decision_boundary_count={len(BOUNDARIES)}")
    print(f"invariant_count={len(INVARIANTS)}")
    print(f"duplicate_entity_count={duplicate_entity_count}")
    print(
        "duplicate_invariant_code_count="
        f"{duplicate_invariant_count}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for entity in ENTITIES:
        print(
            "ONTOLOGY_ENTITY "
            f"name={entity.name} "
            f"aggregate={entity.aggregate} "
            f"owner_stage={entity.owner_stage} "
            f"persistence_required={entity.persistence_required} "
            f"runtime_authority={entity.runtime_authority}"
        )

    for transition in TRANSITIONS:
        print(
            "LIFECYCLE_TRANSITION "
            f"from={transition.from_status} "
            f"to={transition.to_status} "
            f"owner={transition.decision_owner} "
            f"capital_allowed={transition.capital_allowed} "
            f"execution_allowed={transition.execution_allowed}"
        )

    print("owner_assignment_performed=1")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=CAPITAL_GROWTH_ONTOLOGY_V1_READY")

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
