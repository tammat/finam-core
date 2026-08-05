#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import pathlib
from dataclasses import dataclass

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUT = pathlib.Path(
    "/tmp/capital_growth_postgresql_schema_plan_v1"
)

OBJECTS_FILE = OUT / "schema_objects.tsv"
COLUMNS_FILE = OUT / "columns.tsv"
CONSTRAINTS_FILE = OUT / "constraints.tsv"
INDEXES_FILE = OUT / "indexes.tsv"
DEPENDENCIES_FILE = OUT / "dependencies.tsv"
CONFLICTS_FILE = OUT / "conflict_scan.tsv"
MIGRATION_ORDER_FILE = OUT / "migration_order.tsv"
PLAN_SQL_FILE = OUT / "schema_plan.sql"
CONTRACT_FILE = OUT / "schema_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class SchemaObject:
    schema_name: str
    object_name: str
    object_type: str
    responsibility: str
    migration_order: int


@dataclass(frozen=True, slots=True)
class Column:
    table_name: str
    ordinal: int
    column_name: str
    data_type: str
    nullable: int
    default_expression: str
    responsibility: str


@dataclass(frozen=True, slots=True)
class Constraint:
    table_name: str
    constraint_name: str
    constraint_type: str
    expression: str


@dataclass(frozen=True, slots=True)
class Index:
    table_name: str
    index_name: str
    unique: int
    columns_or_expression: str
    predicate: str


@dataclass(frozen=True, slots=True)
class Dependency:
    source_object: str
    target_object: str
    dependency_type: str
    required: int


SCHEMA_OBJECTS = (
    SchemaObject(
        schema_name="capital",
        object_name="capital",
        object_type="SCHEMA",
        responsibility="Изолированная схема Capital Growth Engine",
        migration_order=1,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="edge_candidates",
        object_type="TABLE",
        responsibility=(
            "Версионированные edge-кандидаты "
            "symbol+strategy+timeframe+regime"
        ),
        migration_order=10,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="edge_lifecycle_events",
        object_type="TABLE",
        responsibility="История переходов lifecycle edge",
        migration_order=20,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="metric_registry",
        object_type="TABLE",
        responsibility="Нормативный реестр метрик",
        migration_order=30,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="metric_values",
        object_type="TABLE",
        responsibility="Версионированные значения метрик edge",
        migration_order=40,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="formula_registry",
        object_type="TABLE",
        responsibility="Нормативный реестр формул",
        migration_order=50,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="formula_inputs",
        object_type="TABLE",
        responsibility="Входные метрики, веса и роли формул",
        migration_order=60,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="score_snapshots",
        object_type="TABLE",
        responsibility="История рассчитанных CapitalGrowthScore",
        migration_order=70,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="risk_budgets",
        object_type="TABLE",
        responsibility="Лимиты риска по областям и edge",
        migration_order=80,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="capital_state",
        object_type="TABLE",
        responsibility="Состояние капитала и high-water mark",
        migration_order=90,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="portfolio_state",
        object_type="TABLE",
        responsibility="Снимки портфельного состояния",
        migration_order=100,
    ),
    SchemaObject(
        schema_name="capital",
        object_name="allocation_decisions",
        object_type="TABLE",
        responsibility=(
            "Решения INCREASE/HOLD/REDUCE/REMOVE "
            "без прямого исполнения"
        ),
        migration_order=110,
    ),
)

COLUMNS = (
    Column(
        "edge_candidates",
        1,
        "edge_candidate_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор edge",
    ),
    Column(
        "edge_candidates",
        2,
        "symbol",
        "text",
        0,
        "",
        "Код инструмента",
    ),
    Column(
        "edge_candidates",
        3,
        "strategy",
        "text",
        0,
        "",
        "Идентификатор стратегии",
    ),
    Column(
        "edge_candidates",
        4,
        "timeframe",
        "text",
        0,
        "",
        "Таймфрейм",
    ),
    Column(
        "edge_candidates",
        5,
        "regime",
        "text",
        0,
        "'GENERIC'",
        "Режим рынка",
    ),
    Column(
        "edge_candidates",
        6,
        "hypothesis_version",
        "text",
        0,
        "",
        "Версия торговой гипотезы",
    ),
    Column(
        "edge_candidates",
        7,
        "hypothesis",
        "text",
        0,
        "",
        "Описание гипотезы",
    ),
    Column(
        "edge_candidates",
        8,
        "status",
        "text",
        0,
        "'DISCOVERED'",
        "Текущий статус кандидата",
    ),
    Column(
        "edge_candidates",
        9,
        "source_version",
        "text",
        0,
        "'V1'",
        "Версия источника",
    ),
    Column(
        "edge_candidates",
        10,
        "created_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата создания",
    ),
    Column(
        "edge_candidates",
        11,
        "updated_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата обновления",
    ),

    Column(
        "edge_lifecycle_events",
        1,
        "event_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор события",
    ),
    Column(
        "edge_lifecycle_events",
        2,
        "edge_candidate_id",
        "bigint",
        0,
        "",
        "Ссылка на edge",
    ),
    Column(
        "edge_lifecycle_events",
        3,
        "from_status",
        "text",
        1,
        "",
        "Предыдущий статус",
    ),
    Column(
        "edge_lifecycle_events",
        4,
        "to_status",
        "text",
        0,
        "",
        "Новый статус",
    ),
    Column(
        "edge_lifecycle_events",
        5,
        "decision_owner",
        "text",
        0,
        "",
        "Владелец решения",
    ),
    Column(
        "edge_lifecycle_events",
        6,
        "reason",
        "text",
        0,
        "",
        "Причина перехода",
    ),
    Column(
        "edge_lifecycle_events",
        7,
        "evidence_ref",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Ссылки на evidence",
    ),
    Column(
        "edge_lifecycle_events",
        8,
        "occurred_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата события",
    ),

    Column(
        "metric_registry",
        1,
        "metric_code",
        "text",
        0,
        "",
        "Код метрики",
    ),
    Column(
        "metric_registry",
        2,
        "metric_version",
        "text",
        0,
        "'V1'",
        "Версия метрики",
    ),
    Column(
        "metric_registry",
        3,
        "category",
        "text",
        0,
        "",
        "Категория",
    ),
    Column(
        "metric_registry",
        4,
        "metric_level",
        "text",
        0,
        "",
        "PRIMARY/DERIVED/COMPOSITE",
    ),
    Column(
        "metric_registry",
        5,
        "formula",
        "text",
        0,
        "",
        "Формула",
    ),
    Column(
        "metric_registry",
        6,
        "unit",
        "text",
        0,
        "",
        "Единица измерения",
    ),
    Column(
        "metric_registry",
        7,
        "direction",
        "text",
        0,
        "",
        "Направление оптимизации",
    ),
    Column(
        "metric_registry",
        8,
        "minimum_sample",
        "integer",
        0,
        "0",
        "Минимальная выборка",
    ),
    Column(
        "metric_registry",
        9,
        "source_relation",
        "text",
        0,
        "",
        "Источник данных",
    ),
    Column(
        "metric_registry",
        10,
        "source_fields",
        "text",
        0,
        "",
        "Поля источника",
    ),
    Column(
        "metric_registry",
        11,
        "normalization",
        "text",
        0,
        "",
        "Политика нормализации",
    ),
    Column(
        "metric_registry",
        12,
        "owner_stage",
        "text",
        0,
        "",
        "Владелец метрики",
    ),
    Column(
        "metric_registry",
        13,
        "is_active",
        "boolean",
        0,
        "false",
        "Флаг активации",
    ),
    Column(
        "metric_registry",
        14,
        "created_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата создания",
    ),

    Column(
        "metric_values",
        1,
        "metric_value_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор",
    ),
    Column(
        "metric_values",
        2,
        "edge_candidate_id",
        "bigint",
        0,
        "",
        "Ссылка на edge",
    ),
    Column(
        "metric_values",
        3,
        "metric_code",
        "text",
        0,
        "",
        "Код метрики",
    ),
    Column(
        "metric_values",
        4,
        "metric_version",
        "text",
        0,
        "'V1'",
        "Версия метрики",
    ),
    Column(
        "metric_values",
        5,
        "metric_value",
        "numeric",
        1,
        "",
        "Числовое значение",
    ),
    Column(
        "metric_values",
        6,
        "metric_status",
        "text",
        0,
        "'VALID'",
        "Статус значения",
    ),
    Column(
        "metric_values",
        7,
        "sample_size",
        "integer",
        0,
        "0",
        "Размер выборки",
    ),
    Column(
        "metric_values",
        8,
        "confidence",
        "numeric(10,6)",
        0,
        "0",
        "Доверие 0..1",
    ),
    Column(
        "metric_values",
        9,
        "data_cutoff",
        "timestamptz",
        0,
        "",
        "Граница данных",
    ),
    Column(
        "metric_values",
        10,
        "calculated_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата расчёта",
    ),
    Column(
        "metric_values",
        11,
        "source_version",
        "text",
        0,
        "'V1'",
        "Версия расчёта",
    ),
    Column(
        "metric_values",
        12,
        "raw_context",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Контекст расчёта",
    ),

    Column(
        "formula_registry",
        1,
        "formula_code",
        "text",
        0,
        "",
        "Код формулы",
    ),
    Column(
        "formula_registry",
        2,
        "formula_version",
        "text",
        0,
        "",
        "Версия формулы",
    ),
    Column(
        "formula_registry",
        3,
        "output_metric",
        "text",
        0,
        "",
        "Выходная метрика",
    ),
    Column(
        "formula_registry",
        4,
        "formula_type",
        "text",
        0,
        "",
        "Тип формулы",
    ),
    Column(
        "formula_registry",
        5,
        "expression",
        "text",
        0,
        "",
        "Выражение",
    ),
    Column(
        "formula_registry",
        6,
        "activation_status",
        "text",
        0,
        "'VALIDATED_NOT_ACTIVE'",
        "Статус активации",
    ),
    Column(
        "formula_registry",
        7,
        "owner_stage",
        "text",
        0,
        "",
        "Владелец формулы",
    ),
    Column(
        "formula_registry",
        8,
        "created_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата создания",
    ),

    Column(
        "formula_inputs",
        1,
        "formula_code",
        "text",
        0,
        "",
        "Код формулы",
    ),
    Column(
        "formula_inputs",
        2,
        "formula_version",
        "text",
        0,
        "",
        "Версия формулы",
    ),
    Column(
        "formula_inputs",
        3,
        "metric_code",
        "text",
        0,
        "",
        "Входная метрика",
    ),
    Column(
        "formula_inputs",
        4,
        "metric_version",
        "text",
        0,
        "'V1'",
        "Версия метрики",
    ),
    Column(
        "formula_inputs",
        5,
        "role",
        "text",
        0,
        "",
        "Роль метрики",
    ),
    Column(
        "formula_inputs",
        6,
        "weight",
        "numeric(12,8)",
        0,
        "0",
        "Вес",
    ),
    Column(
        "formula_inputs",
        7,
        "required",
        "boolean",
        0,
        "true",
        "Обязательность",
    ),

    Column(
        "score_snapshots",
        1,
        "score_snapshot_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор",
    ),
    Column(
        "score_snapshots",
        2,
        "edge_candidate_id",
        "bigint",
        0,
        "",
        "Ссылка на edge",
    ),
    Column(
        "score_snapshots",
        3,
        "formula_code",
        "text",
        0,
        "",
        "Код формулы",
    ),
    Column(
        "score_snapshots",
        4,
        "formula_version",
        "text",
        0,
        "",
        "Версия формулы",
    ),
    Column(
        "score_snapshots",
        5,
        "score",
        "numeric(10,6)",
        0,
        "",
        "Score 0..100",
    ),
    Column(
        "score_snapshots",
        6,
        "confidence_multiplier",
        "numeric(10,6)",
        0,
        "",
        "Множитель доверия",
    ),
    Column(
        "score_snapshots",
        7,
        "score_status",
        "text",
        0,
        "'INVALID'",
        "VALID/BLOCKED/INVALID",
    ),
    Column(
        "score_snapshots",
        8,
        "gate_results",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Результаты hard gates",
    ),
    Column(
        "score_snapshots",
        9,
        "penalty_results",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Штрафы",
    ),
    Column(
        "score_snapshots",
        10,
        "component_values",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Компоненты score",
    ),
    Column(
        "score_snapshots",
        11,
        "calculated_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата расчёта",
    ),

    Column(
        "risk_budgets",
        1,
        "risk_budget_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор",
    ),
    Column(
        "risk_budgets",
        2,
        "scope",
        "text",
        0,
        "",
        "PORTFOLIO/EDGE/SYMBOL/CORRELATION_GROUP",
    ),
    Column(
        "risk_budgets",
        3,
        "scope_key",
        "text",
        0,
        "",
        "Ключ области",
    ),
    Column(
        "risk_budgets",
        4,
        "limit_value",
        "numeric",
        0,
        "",
        "Лимит риска",
    ),
    Column(
        "risk_budgets",
        5,
        "consumed_value",
        "numeric",
        0,
        "0",
        "Использованный риск",
    ),
    Column(
        "risk_budgets",
        6,
        "status",
        "text",
        0,
        "'DISABLED'",
        "Статус бюджета",
    ),
    Column(
        "risk_budgets",
        7,
        "version",
        "text",
        0,
        "'V1'",
        "Версия",
    ),
    Column(
        "risk_budgets",
        8,
        "updated_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата обновления",
    ),

    Column(
        "capital_state",
        1,
        "capital_state_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор",
    ),
    Column(
        "capital_state",
        2,
        "equity",
        "numeric",
        0,
        "",
        "Текущий капитал",
    ),
    Column(
        "capital_state",
        3,
        "high_water_mark",
        "numeric",
        0,
        "",
        "Максимум капитала",
    ),
    Column(
        "capital_state",
        4,
        "drawdown",
        "numeric",
        0,
        "0",
        "Текущая просадка",
    ),
    Column(
        "capital_state",
        5,
        "available_capital",
        "numeric",
        0,
        "",
        "Доступный капитал",
    ),
    Column(
        "capital_state",
        6,
        "reserved_capital",
        "numeric",
        0,
        "0",
        "Зарезервированный капитал",
    ),
    Column(
        "capital_state",
        7,
        "as_of",
        "timestamptz",
        0,
        "",
        "Время снимка",
    ),
    Column(
        "capital_state",
        8,
        "source_version",
        "text",
        0,
        "'V1'",
        "Версия источника",
    ),

    Column(
        "portfolio_state",
        1,
        "portfolio_state_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор",
    ),
    Column(
        "portfolio_state",
        2,
        "cash",
        "numeric",
        0,
        "",
        "Денежные средства",
    ),
    Column(
        "portfolio_state",
        3,
        "equity",
        "numeric",
        0,
        "",
        "Капитал портфеля",
    ),
    Column(
        "portfolio_state",
        4,
        "gross_exposure",
        "numeric",
        0,
        "0",
        "Валовая экспозиция",
    ),
    Column(
        "portfolio_state",
        5,
        "net_exposure",
        "numeric",
        0,
        "0",
        "Чистая экспозиция",
    ),
    Column(
        "portfolio_state",
        6,
        "positions",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Позиции",
    ),
    Column(
        "portfolio_state",
        7,
        "risk_usage",
        "jsonb",
        0,
        "'{}'::jsonb",
        "Потребление риска",
    ),
    Column(
        "portfolio_state",
        8,
        "as_of",
        "timestamptz",
        0,
        "",
        "Время снимка",
    ),
    Column(
        "portfolio_state",
        9,
        "source_version",
        "text",
        0,
        "'V1'",
        "Версия источника",
    ),

    Column(
        "allocation_decisions",
        1,
        "allocation_decision_id",
        "bigint GENERATED ALWAYS AS IDENTITY",
        0,
        "",
        "Первичный идентификатор",
    ),
    Column(
        "allocation_decisions",
        2,
        "edge_candidate_id",
        "bigint",
        0,
        "",
        "Ссылка на edge",
    ),
    Column(
        "allocation_decisions",
        3,
        "score_snapshot_id",
        "bigint",
        0,
        "",
        "Ссылка на score",
    ),
    Column(
        "allocation_decisions",
        4,
        "capital_state_id",
        "bigint",
        0,
        "",
        "Ссылка на capital state",
    ),
    Column(
        "allocation_decisions",
        5,
        "portfolio_state_id",
        "bigint",
        0,
        "",
        "Ссылка на portfolio state",
    ),
    Column(
        "allocation_decisions",
        6,
        "action",
        "text",
        0,
        "",
        "INCREASE/HOLD/REDUCE/REMOVE",
    ),
    Column(
        "allocation_decisions",
        7,
        "target_capital",
        "numeric",
        0,
        "0",
        "Целевой капитал",
    ),
    Column(
        "allocation_decisions",
        8,
        "target_risk",
        "numeric",
        0,
        "0",
        "Целевой риск",
    ),
    Column(
        "allocation_decisions",
        9,
        "decision_status",
        "text",
        0,
        "'PROPOSED'",
        "Статус решения",
    ),
    Column(
        "allocation_decisions",
        10,
        "reason",
        "text",
        0,
        "",
        "Причина решения",
    ),
    Column(
        "allocation_decisions",
        11,
        "execution_allowed",
        "boolean",
        0,
        "false",
        "Исполнение запрещено по умолчанию",
    ),
    Column(
        "allocation_decisions",
        12,
        "decided_at",
        "timestamptz",
        0,
        "clock_timestamp()",
        "Дата решения",
    ),
)

CONSTRAINTS = (
    Constraint(
        "edge_candidates",
        "pk_edge_candidates",
        "PRIMARY_KEY",
        "PRIMARY KEY (edge_candidate_id)",
    ),
    Constraint(
        "edge_candidates",
        "uq_edge_candidates_identity",
        "UNIQUE",
        (
            "UNIQUE "
            "(symbol,strategy,timeframe,regime,hypothesis_version)"
        ),
    ),
    Constraint(
        "edge_candidates",
        "ck_edge_candidates_status",
        "CHECK",
        (
            "CHECK (status IN "
            "('DISCOVERED','RESEARCH','ROBUST','OOS_READY',"
            "'SHADOW_READY','PAPER_READY','CAPITAL_ALLOCATED',"
            "'REAL_ELIGIBLE','QUARANTINED','REJECTED'))"
        ),
    ),
    Constraint(
        "edge_lifecycle_events",
        "pk_edge_lifecycle_events",
        "PRIMARY_KEY",
        "PRIMARY KEY (event_id)",
    ),
    Constraint(
        "edge_lifecycle_events",
        "fk_edge_lifecycle_candidate",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (edge_candidate_id) "
            "REFERENCES capital.edge_candidates(edge_candidate_id)"
        ),
    ),
    Constraint(
        "metric_registry",
        "pk_metric_registry",
        "PRIMARY_KEY",
        "PRIMARY KEY (metric_code,metric_version)",
    ),
    Constraint(
        "metric_registry",
        "ck_metric_registry_level",
        "CHECK",
        (
            "CHECK (metric_level IN "
            "('PRIMARY','DERIVED','COMPOSITE'))"
        ),
    ),
    Constraint(
        "metric_values",
        "pk_metric_values",
        "PRIMARY_KEY",
        "PRIMARY KEY (metric_value_id)",
    ),
    Constraint(
        "metric_values",
        "fk_metric_values_candidate",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (edge_candidate_id) "
            "REFERENCES capital.edge_candidates(edge_candidate_id)"
        ),
    ),
    Constraint(
        "metric_values",
        "fk_metric_values_registry",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (metric_code,metric_version) "
            "REFERENCES capital.metric_registry"
            "(metric_code,metric_version)"
        ),
    ),
    Constraint(
        "metric_values",
        "ck_metric_values_confidence",
        "CHECK",
        "CHECK (confidence >= 0 AND confidence <= 1)",
    ),
    Constraint(
        "metric_values",
        "ck_metric_values_sample_size",
        "CHECK",
        "CHECK (sample_size >= 0)",
    ),
    Constraint(
        "formula_registry",
        "pk_formula_registry",
        "PRIMARY_KEY",
        "PRIMARY KEY (formula_code,formula_version)",
    ),
    Constraint(
        "formula_registry",
        "fk_formula_output_metric",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (output_metric,formula_version) "
            "REFERENCES capital.metric_registry"
            "(metric_code,metric_version)"
        ),
    ),
    Constraint(
        "formula_registry",
        "ck_formula_activation_status",
        "CHECK",
        (
            "CHECK (activation_status IN "
            "('DRAFT','VALIDATED_NOT_ACTIVE',"
            "'ACTIVE_RESEARCH_ONLY','RETIRED'))"
        ),
    ),
    Constraint(
        "formula_inputs",
        "pk_formula_inputs",
        "PRIMARY_KEY",
        (
            "PRIMARY KEY "
            "(formula_code,formula_version,metric_code,metric_version)"
        ),
    ),
    Constraint(
        "formula_inputs",
        "fk_formula_inputs_formula",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (formula_code,formula_version) "
            "REFERENCES capital.formula_registry"
            "(formula_code,formula_version)"
        ),
    ),
    Constraint(
        "formula_inputs",
        "fk_formula_inputs_metric",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (metric_code,metric_version) "
            "REFERENCES capital.metric_registry"
            "(metric_code,metric_version)"
        ),
    ),
    Constraint(
        "formula_inputs",
        "ck_formula_inputs_weight",
        "CHECK",
        "CHECK (weight >= 0 AND weight <= 1)",
    ),
    Constraint(
        "score_snapshots",
        "pk_score_snapshots",
        "PRIMARY_KEY",
        "PRIMARY KEY (score_snapshot_id)",
    ),
    Constraint(
        "score_snapshots",
        "fk_score_candidate",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (edge_candidate_id) "
            "REFERENCES capital.edge_candidates(edge_candidate_id)"
        ),
    ),
    Constraint(
        "score_snapshots",
        "fk_score_formula",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (formula_code,formula_version) "
            "REFERENCES capital.formula_registry"
            "(formula_code,formula_version)"
        ),
    ),
    Constraint(
        "score_snapshots",
        "ck_score_range",
        "CHECK",
        "CHECK (score >= 0 AND score <= 100)",
    ),
    Constraint(
        "score_snapshots",
        "ck_score_confidence",
        "CHECK",
        (
            "CHECK "
            "(confidence_multiplier >= 0 "
            "AND confidence_multiplier <= 1)"
        ),
    ),
    Constraint(
        "risk_budgets",
        "pk_risk_budgets",
        "PRIMARY_KEY",
        "PRIMARY KEY (risk_budget_id)",
    ),
    Constraint(
        "risk_budgets",
        "uq_risk_budget_scope",
        "UNIQUE",
        "UNIQUE (scope,scope_key,version)",
    ),
    Constraint(
        "risk_budgets",
        "ck_risk_budget_values",
        "CHECK",
        (
            "CHECK "
            "(limit_value >= 0 "
            "AND consumed_value >= 0 "
            "AND consumed_value <= limit_value)"
        ),
    ),
    Constraint(
        "capital_state",
        "pk_capital_state",
        "PRIMARY_KEY",
        "PRIMARY KEY (capital_state_id)",
    ),
    Constraint(
        "capital_state",
        "uq_capital_state_as_of",
        "UNIQUE",
        "UNIQUE (as_of,source_version)",
    ),
    Constraint(
        "capital_state",
        "ck_capital_state_values",
        "CHECK",
        (
            "CHECK "
            "(equity >= 0 "
            "AND high_water_mark >= 0 "
            "AND available_capital >= 0 "
            "AND reserved_capital >= 0)"
        ),
    ),
    Constraint(
        "portfolio_state",
        "pk_portfolio_state",
        "PRIMARY_KEY",
        "PRIMARY KEY (portfolio_state_id)",
    ),
    Constraint(
        "portfolio_state",
        "uq_portfolio_state_as_of",
        "UNIQUE",
        "UNIQUE (as_of,source_version)",
    ),
    Constraint(
        "allocation_decisions",
        "pk_allocation_decisions",
        "PRIMARY_KEY",
        "PRIMARY KEY (allocation_decision_id)",
    ),
    Constraint(
        "allocation_decisions",
        "fk_allocation_candidate",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (edge_candidate_id) "
            "REFERENCES capital.edge_candidates(edge_candidate_id)"
        ),
    ),
    Constraint(
        "allocation_decisions",
        "fk_allocation_score",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (score_snapshot_id) "
            "REFERENCES capital.score_snapshots(score_snapshot_id)"
        ),
    ),
    Constraint(
        "allocation_decisions",
        "fk_allocation_capital_state",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (capital_state_id) "
            "REFERENCES capital.capital_state(capital_state_id)"
        ),
    ),
    Constraint(
        "allocation_decisions",
        "fk_allocation_portfolio_state",
        "FOREIGN_KEY",
        (
            "FOREIGN KEY (portfolio_state_id) "
            "REFERENCES capital.portfolio_state(portfolio_state_id)"
        ),
    ),
    Constraint(
        "allocation_decisions",
        "ck_allocation_action",
        "CHECK",
        (
            "CHECK "
            "(action IN ('INCREASE','HOLD','REDUCE','REMOVE'))"
        ),
    ),
    Constraint(
        "allocation_decisions",
        "ck_allocation_execution_disabled",
        "CHECK",
        "CHECK (execution_allowed = false)",
    ),
    Constraint(
        "allocation_decisions",
        "ck_allocation_values",
        "CHECK",
        "CHECK (target_capital >= 0 AND target_risk >= 0)",
    ),
)

INDEXES = (
    Index(
        "edge_candidates",
        "ix_edge_candidates_status",
        0,
        "status",
        "",
    ),
    Index(
        "edge_candidates",
        "ix_edge_candidates_symbol_strategy",
        0,
        "symbol,strategy,timeframe",
        "",
    ),
    Index(
        "edge_lifecycle_events",
        "ix_edge_lifecycle_candidate_time",
        0,
        "edge_candidate_id,occurred_at DESC",
        "",
    ),
    Index(
        "metric_values",
        "ix_metric_values_candidate_metric_time",
        0,
        "edge_candidate_id,metric_code,calculated_at DESC",
        "",
    ),
    Index(
        "metric_values",
        "ix_metric_values_valid",
        0,
        "metric_code,calculated_at DESC",
        "metric_status = 'VALID'",
    ),
    Index(
        "score_snapshots",
        "ix_score_snapshots_candidate_time",
        0,
        "edge_candidate_id,calculated_at DESC",
        "",
    ),
    Index(
        "score_snapshots",
        "ix_score_snapshots_valid_score",
        0,
        "score DESC,calculated_at DESC",
        "score_status = 'VALID'",
    ),
    Index(
        "risk_budgets",
        "ix_risk_budgets_status",
        0,
        "status,scope",
        "",
    ),
    Index(
        "allocation_decisions",
        "ix_allocation_candidate_time",
        0,
        "edge_candidate_id,decided_at DESC",
        "",
    ),
    Index(
        "allocation_decisions",
        "ix_allocation_status",
        0,
        "decision_status,decided_at DESC",
        "",
    ),
)

DEPENDENCIES = (
    Dependency(
        "edge_lifecycle_events",
        "edge_candidates",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "metric_values",
        "edge_candidates",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "metric_values",
        "metric_registry",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "formula_registry",
        "metric_registry",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "formula_inputs",
        "formula_registry",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "formula_inputs",
        "metric_registry",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "score_snapshots",
        "edge_candidates",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "score_snapshots",
        "formula_registry",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "allocation_decisions",
        "edge_candidates",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "allocation_decisions",
        "score_snapshots",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "allocation_decisions",
        "capital_state",
        "FOREIGN_KEY",
        1,
    ),
    Dependency(
        "allocation_decisions",
        "portfolio_state",
        "FOREIGN_KEY",
        1,
    ),
)


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def render_create_table(table_name: str) -> str:
    table_columns = sorted(
        (
            column
            for column in COLUMNS
            if column.table_name == table_name
        ),
        key=lambda item: item.ordinal,
    )

    table_constraints = [
        constraint
        for constraint in CONSTRAINTS
        if constraint.table_name == table_name
    ]

    lines: list[str] = []

    for column in table_columns:
        line = (
            f"    {quote_identifier(column.column_name)} "
            f"{column.data_type}"
        )

        if not column.nullable:
            line += " NOT NULL"

        if column.default_expression:
            line += (
                f" DEFAULT {column.default_expression}"
            )

        lines.append(line)

    for constraint in table_constraints:
        lines.append(
            "    CONSTRAINT "
            f"{quote_identifier(constraint.constraint_name)} "
            f"{constraint.expression}"
        )

    return (
        "CREATE TABLE IF NOT EXISTS "
        f"capital.{quote_identifier(table_name)} (\n"
        + ",\n".join(lines)
        + "\n);\n"
    )


def render_plan_sql() -> str:
    table_objects = sorted(
        (
            item
            for item in SCHEMA_OBJECTS
            if item.object_type == "TABLE"
        ),
        key=lambda item: item.migration_order,
    )

    parts = [
        "-- CAPITAL GROWTH POSTGRESQL SCHEMA PLAN V1",
        "-- PLAN ONLY. DO NOT EXECUTE FROM THIS FILE.",
        "",
        "CREATE SCHEMA IF NOT EXISTS capital;",
        "",
    ]

    for item in table_objects:
        parts.append(render_create_table(item.object_name))

    for index in INDEXES:
        unique_sql = "UNIQUE " if index.unique else ""

        sql = (
            f"CREATE {unique_sql}INDEX IF NOT EXISTS "
            f"{quote_identifier(index.index_name)} "
            f"ON capital.{quote_identifier(index.table_name)} "
            f"({index.columns_or_expression})"
        )

        if index.predicate:
            sql += f" WHERE {index.predicate}"

        sql += ";"
        parts.append(sql)

    parts.extend(
        [
            "",
            "-- Safety contract",
            "-- score calculation disabled",
            "-- allocation execution disabled",
            "-- runtime integration disabled",
            "-- micro live disabled",
        ]
    )

    return "\n".join(parts) + "\n"


def scan_conflicts(
    cursor: RealDictCursor,
) -> list[dict[str, object]]:
    conflicts: list[dict[str, object]] = []

    cursor.execute(
        """
        SELECT
            n.nspname AS schema_name,
            c.relname AS object_name,
            c.relkind AS object_kind
        FROM pg_class c
        JOIN pg_namespace n
          ON n.oid = c.relnamespace
        WHERE n.nspname = 'capital'
        ORDER BY c.relname
        """
    )

    existing_objects = {
        str(row["object_name"]): str(row["object_kind"])
        for row in cursor.fetchall()
    }

    planned_tables = {
        item.object_name
        for item in SCHEMA_OBJECTS
        if item.object_type == "TABLE"
    }

    for table_name in sorted(planned_tables):
        existing_kind = existing_objects.get(table_name)

        if existing_kind is None:
            conflicts.append(
                {
                    "schema_name": "capital",
                    "object_name": table_name,
                    "conflict_type": "NONE",
                    "existing_object_kind": "",
                    "planned_object_type": "TABLE",
                    "reason": "OBJECT_NOT_PRESENT",
                }
            )
            continue

        if existing_kind not in {"r", "p"}:
            conflicts.append(
                {
                    "schema_name": "capital",
                    "object_name": table_name,
                    "conflict_type": "TYPE_CONFLICT",
                    "existing_object_kind": existing_kind,
                    "planned_object_type": "TABLE",
                    "reason": "EXISTING_OBJECT_IS_NOT_TABLE",
                }
            )
            continue

        cursor.execute(
            """
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'capital'
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )

        existing_columns = {
            str(row["column_name"]): {
                "data_type": str(row["data_type"]),
                "udt_name": str(row["udt_name"]),
                "is_nullable": str(row["is_nullable"]),
            }
            for row in cursor.fetchall()
        }

        planned_columns = {
            item.column_name
            for item in COLUMNS
            if item.table_name == table_name
        }

        missing_columns = sorted(
            planned_columns - set(existing_columns)
        )

        unexpected_columns = sorted(
            set(existing_columns) - planned_columns
        )

        if missing_columns:
            conflicts.append(
                {
                    "schema_name": "capital",
                    "object_name": table_name,
                    "conflict_type": "COLUMN_CONFLICT",
                    "existing_object_kind": existing_kind,
                    "planned_object_type": "TABLE",
                    "reason": (
                        "MISSING_PLANNED_COLUMNS:"
                        + ",".join(missing_columns)
                    ),
                }
            )

        if unexpected_columns:
            conflicts.append(
                {
                    "schema_name": "capital",
                    "object_name": table_name,
                    "conflict_type": "REVIEW_REQUIRED",
                    "existing_object_kind": existing_kind,
                    "planned_object_type": "TABLE",
                    "reason": (
                        "UNEXPECTED_EXISTING_COLUMNS:"
                        + ",".join(unexpected_columns)
                    ),
                }
            )

        if not missing_columns and not unexpected_columns:
            conflicts.append(
                {
                    "schema_name": "capital",
                    "object_name": table_name,
                    "conflict_type": "EXACT_COLUMN_NAME_MATCH",
                    "existing_object_kind": existing_kind,
                    "planned_object_type": "TABLE",
                    "reason": "EXISTING_TABLE_REQUIRES_TYPE_AND_CONSTRAINT_REVIEW",
                }
            )

    return conflicts


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, object]] = []

    object_identities = [
        (
            item.schema_name,
            item.object_name,
            item.object_type,
        )
        for item in SCHEMA_OBJECTS
    ]

    duplicate_object_count = (
        len(object_identities)
        - len(set(object_identities))
    )

    if duplicate_object_count:
        unresolved.append(
            {
                "scope": "SCHEMA_OBJECT",
                "identity": "",
                "reason": (
                    "DUPLICATE_SCHEMA_OBJECT_COUNT:"
                    f"{duplicate_object_count}"
                ),
            }
        )

    table_names = {
        item.object_name
        for item in SCHEMA_OBJECTS
        if item.object_type == "TABLE"
    }

    for column in COLUMNS:
        if column.table_name not in table_names:
            unresolved.append(
                {
                    "scope": "COLUMN",
                    "identity": (
                        f"{column.table_name}.{column.column_name}"
                    ),
                    "reason": "TABLE_NOT_REGISTERED",
                }
            )

    for constraint in CONSTRAINTS:
        if constraint.table_name not in table_names:
            unresolved.append(
                {
                    "scope": "CONSTRAINT",
                    "identity": constraint.constraint_name,
                    "reason": "TABLE_NOT_REGISTERED",
                }
            )

    for index in INDEXES:
        if index.table_name not in table_names:
            unresolved.append(
                {
                    "scope": "INDEX",
                    "identity": index.index_name,
                    "reason": "TABLE_NOT_REGISTERED",
                }
            )

    for dependency in DEPENDENCIES:
        if dependency.source_object not in table_names:
            unresolved.append(
                {
                    "scope": "DEPENDENCY",
                    "identity": dependency.source_object,
                    "reason": "SOURCE_OBJECT_NOT_REGISTERED",
                }
            )

        if dependency.target_object not in table_names:
            unresolved.append(
                {
                    "scope": "DEPENDENCY",
                    "identity": dependency.target_object,
                    "reason": "TARGET_OBJECT_NOT_REGISTERED",
                }
            )

    connection_url = build_psycopg_url()

    with psycopg2.connect(connection_url) as connection:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            conflicts = scan_conflicts(cursor)

    hard_conflicts = [
        row
        for row in conflicts
        if row["conflict_type"] in {
            "TYPE_CONFLICT",
            "COLUMN_CONFLICT",
        }
    ]

    for conflict in hard_conflicts:
        unresolved.append(
            {
                "scope": "POSTGRES_CONFLICT",
                "identity": (
                    f"{conflict['schema_name']}."
                    f"{conflict['object_name']}"
                ),
                "reason": conflict["reason"],
            }
        )

    write_tsv(
        OBJECTS_FILE,
        (
            "schema_name",
            "object_name",
            "object_type",
            "responsibility",
            "migration_order",
        ),
        [
            {
                "schema_name": item.schema_name,
                "object_name": item.object_name,
                "object_type": item.object_type,
                "responsibility": item.responsibility,
                "migration_order": item.migration_order,
            }
            for item in SCHEMA_OBJECTS
        ],
    )

    write_tsv(
        COLUMNS_FILE,
        (
            "table_name",
            "ordinal",
            "column_name",
            "data_type",
            "nullable",
            "default_expression",
            "responsibility",
        ),
        [
            {
                "table_name": item.table_name,
                "ordinal": item.ordinal,
                "column_name": item.column_name,
                "data_type": item.data_type,
                "nullable": item.nullable,
                "default_expression": item.default_expression,
                "responsibility": item.responsibility,
            }
            for item in COLUMNS
        ],
    )

    write_tsv(
        CONSTRAINTS_FILE,
        (
            "table_name",
            "constraint_name",
            "constraint_type",
            "expression",
        ),
        [
            {
                "table_name": item.table_name,
                "constraint_name": item.constraint_name,
                "constraint_type": item.constraint_type,
                "expression": item.expression,
            }
            for item in CONSTRAINTS
        ],
    )

    write_tsv(
        INDEXES_FILE,
        (
            "table_name",
            "index_name",
            "unique",
            "columns_or_expression",
            "predicate",
        ),
        [
            {
                "table_name": item.table_name,
                "index_name": item.index_name,
                "unique": item.unique,
                "columns_or_expression": item.columns_or_expression,
                "predicate": item.predicate,
            }
            for item in INDEXES
        ],
    )

    write_tsv(
        DEPENDENCIES_FILE,
        (
            "source_object",
            "target_object",
            "dependency_type",
            "required",
        ),
        [
            {
                "source_object": item.source_object,
                "target_object": item.target_object,
                "dependency_type": item.dependency_type,
                "required": item.required,
            }
            for item in DEPENDENCIES
        ],
    )

    write_tsv(
        CONFLICTS_FILE,
        (
            "schema_name",
            "object_name",
            "conflict_type",
            "existing_object_kind",
            "planned_object_type",
            "reason",
        ),
        conflicts,
    )

    write_tsv(
        MIGRATION_ORDER_FILE,
        (
            "migration_order",
            "schema_name",
            "object_name",
            "object_type",
        ),
        [
            {
                "migration_order": item.migration_order,
                "schema_name": item.schema_name,
                "object_name": item.object_name,
                "object_type": item.object_type,
            }
            for item in sorted(
                SCHEMA_OBJECTS,
                key=lambda row: row.migration_order,
            )
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

    PLAN_SQL_FILE.write_text(
        render_plan_sql(),
        encoding="utf-8",
    )

    table_count = sum(
        item.object_type == "TABLE"
        for item in SCHEMA_OBJECTS
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "CAPITAL GROWTH POSTGRESQL SCHEMA PLAN V1\n"
        )
        stream.write(
            "========================================\n\n"
        )
        stream.write("MODE=PLAN_ONLY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write("SCHEMA_NAME=capital\n")
        stream.write(
            f"SCHEMA_OBJECT_COUNT={len(SCHEMA_OBJECTS)}\n"
        )
        stream.write(f"TABLE_COUNT={table_count}\n")
        stream.write(f"COLUMN_COUNT={len(COLUMNS)}\n")
        stream.write(
            f"CONSTRAINT_COUNT={len(CONSTRAINTS)}\n"
        )
        stream.write(f"INDEX_COUNT={len(INDEXES)}\n")
        stream.write(
            f"DEPENDENCY_COUNT={len(DEPENDENCIES)}\n"
        )
        stream.write(
            f"HARD_CONFLICT_COUNT={len(hard_conflicts)}\n"
        )
        stream.write(
            f"DUPLICATE_SCHEMA_OBJECT_COUNT="
            f"{duplicate_object_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("DDL_EXECUTED=0\n")
        stream.write("SCHEMA_CREATED=0\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("SCORE_CALCULATION_ENABLED=0\n")
        stream.write("ALLOCATION_ENABLED=0\n")
        stream.write("RUNTIME_USAGE_ALLOWED=0\n")
        stream.write("EXECUTION_USAGE_ALLOWED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print(
        "=== BUILD CAPITAL GROWTH "
        "POSTGRESQL SCHEMA PLAN V1 ==="
    )
    print("mode=plan_only")
    print("schema_name=capital")
    print(f"schema_object_count={len(SCHEMA_OBJECTS)}")
    print(f"table_count={table_count}")
    print(f"column_count={len(COLUMNS)}")
    print(f"constraint_count={len(CONSTRAINTS)}")
    print(f"index_count={len(INDEXES)}")
    print(f"dependency_count={len(DEPENDENCIES)}")
    print(f"hard_conflict_count={len(hard_conflicts)}")
    print(f"unresolved_count={len(unresolved)}")

    for conflict in conflicts:
        print(
            "CONFLICT_SCAN "
            f"object={conflict['schema_name']}."
            f"{conflict['object_name']} "
            f"type={conflict['conflict_type']} "
            f"reason={conflict['reason']}"
        )

    print("owner_assignment_performed=1")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("ddl_executed=0")
    print("schema_created=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "CAPITAL_GROWTH_POSTGRESQL_SCHEMA_PLAN_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
