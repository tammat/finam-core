#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.experiment_registry_v1 (
    experiment_id BIGSERIAL PRIMARY KEY,

    experiment_code TEXT NOT NULL UNIQUE,
    experiment_name TEXT NOT NULL,
    description TEXT,

    research_domain TEXT DEFAULT 'TRADING_RESEARCH',

    strategy_code TEXT,
    symbol TEXT,
    timeframe TEXT,

    feature_set JSONB DEFAULT '[]'::jsonb,
    model_set JSONB DEFAULT '[]'::jsonb,

    dataset_id TEXT,
    training_period JSONB DEFAULT '{}'::jsonb,
    validation_period JSONB DEFAULT '{}'::jsonb,
    test_period JSONB DEFAULT '{}'::jsonb,

    parameters JSONB DEFAULT '{}'::jsonb,
    hypothesis TEXT,
    result_summary TEXT,

    expectancy NUMERIC,
    profit_factor NUMERIC,
    win_rate NUMERIC,
    drawdown NUMERIC,
    sharpe NUMERIC,
    sortino NUMERIC,

    quality_score NUMERIC,
    stability_score NUMERIC,
    drift_score NUMERIC,

    decision TEXT DEFAULT 'NO_DECISION',

    status TEXT DEFAULT 'DISCOVERED',
    maturity_level TEXT DEFAULT 'RESEARCH',

    approved_for_research BOOLEAN DEFAULT true,
    approved_for_shadow BOOLEAN DEFAULT false,
    approved_for_paper BOOLEAN DEFAULT false,
    approved_for_live BOOLEAN DEFAULT false,

    feature_registry_refs JSONB DEFAULT '[]'::jsonb,
    model_registry_refs JSONB DEFAULT '[]'::jsonb,
    dataset_refs JSONB DEFAULT '[]'::jsonb,
    report_refs JSONB DEFAULT '[]'::jsonb,

    source_of_truth TEXT DEFAULT 'RESEARCH',
    owner TEXT DEFAULT 'Research',

    payload JSONB DEFAULT '{}'::jsonb,

    registry_version TEXT DEFAULT 'EXPERIMENT_REGISTRY_V1',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_experiment_registry_status_v1
ON warehouse.experiment_registry_v1(status);

CREATE INDEX IF NOT EXISTS idx_experiment_registry_maturity_v1
ON warehouse.experiment_registry_v1(maturity_level);

CREATE INDEX IF NOT EXISTS idx_experiment_registry_strategy_v1
ON warehouse.experiment_registry_v1(strategy_code);

CREATE INDEX IF NOT EXISTS idx_experiment_registry_symbol_v1
ON warehouse.experiment_registry_v1(symbol);

CREATE INDEX IF NOT EXISTS idx_experiment_registry_timeframe_v1
ON warehouse.experiment_registry_v1(timeframe);

CREATE INDEX IF NOT EXISTS idx_experiment_registry_decision_v1
ON warehouse.experiment_registry_v1(decision);
"""


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

            cur.execute("""
                SELECT count(*)::int
                FROM information_schema.columns
                WHERE table_schema='warehouse'
                  AND table_name='experiment_registry_v1'
            """)
            columns = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)::int
                FROM pg_indexes
                WHERE schemaname='warehouse'
                  AND tablename='experiment_registry_v1'
            """)
            indexes = cur.fetchone()[0]

    print("=== EXPERIMENT_REGISTRY_SCHEMA_V1 ===")
    print("таблица=warehouse.experiment_registry_v1")
    print(f"колонок={columns}")
    print(f"индексов={indexes}")
    print("назначение=единый_реестр_исследовательских_экспериментов")
    print("связи=features,models,datasets,reports")
    print("статусы=DISCOVERED,REGISTERED,RUNNING,VALIDATED,APPROVED,DEPRECATED,ARCHIVED")
    print("зрелость=RESEARCH,VALIDATED,SHADOW,PAPER,LIVE")
    print("политика_источника=RESEARCH_TO_REGISTRY")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EXPERIMENT_REGISTRY_SCHEMA_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
