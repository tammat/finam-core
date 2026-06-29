#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO warehouse.experiment_registry_v1 (
                    experiment_code,
                    experiment_name,
                    description,
                    research_domain,
                    strategy_code,
                    symbol,
                    timeframe,
                    feature_set,
                    model_set,
                    hypothesis,
                    result_summary,
                    expectancy,
                    profit_factor,
                    win_rate,
                    decision,
                    status,
                    maturity_level,
                    approved_for_research,
                    approved_for_shadow,
                    approved_for_paper,
                    approved_for_live,
                    source_of_truth,
                    owner,
                    payload,
                    updated_at
                )
                VALUES (
                    'EXP-BRM6-RTSX-BR-CONSERVATIVE-BREAKOUT-M5-000001',
                    'BRM6 RTSX BR Conservative Breakout M5',
                    'Первичный исследовательский эксперимент по кандидату BRM6@RTSX / BR_CONSERVATIVE_BREAKOUT / M5',
                    'TRADING_RESEARCH',
                    'BR_CONSERVATIVE_BREAKOUT',
                    'BRM6@RTSX',
                    'M5',
                    '[]'::jsonb,
                    '[]'::jsonb,
                    'Проверка наличия статистического преимущества у найденного кандидата.',
                    'Кандидат найден автоматическим поиском. Требуется forensic audit, robustness и out-of-sample validation.',
                    1.912857,
                    1.942233,
                    46.75,
                    'RESEARCH_CANDIDATE',
                    'REGISTERED',
                    'RESEARCH',
                    true,
                    false,
                    false,
                    false,
                    'GLOBAL_EDGE_DISCOVERY',
                    'Research',
                    jsonb_build_object(
                        'source_candidate', 'MSC-000001',
                        'symbol', 'BRM6@RTSX',
                        'strategy', 'BR_CONSERVATIVE_BREAKOUT',
                        'timeframe', 'M5',
                        'trades', 77,
                        'wins', 36,
                        'losses', 41,
                        'net_pnl', 147.290019,
                        'required_next_steps', jsonb_build_array(
                            'GLOBAL_EDGE_CANDIDATE_FORENSIC_AUDIT_V1',
                            'GLOBAL_EDGE_CANDIDATE_ROBUSTNESS_V1',
                            'OUT_OF_SAMPLE_VALIDATION_PLAN_V1'
                        ),
                        'runtime_changed', false,
                        'execution_changed', false,
                        'orders_changed', false,
                        'fills_changed', false,
                        'micro_live_allowed', false
                    ),
                    now()
                )
                ON CONFLICT(experiment_code) DO UPDATE SET
                    experiment_name=EXCLUDED.experiment_name,
                    description=EXCLUDED.description,
                    research_domain=EXCLUDED.research_domain,
                    strategy_code=EXCLUDED.strategy_code,
                    symbol=EXCLUDED.symbol,
                    timeframe=EXCLUDED.timeframe,
                    hypothesis=EXCLUDED.hypothesis,
                    result_summary=EXCLUDED.result_summary,
                    expectancy=EXCLUDED.expectancy,
                    profit_factor=EXCLUDED.profit_factor,
                    win_rate=EXCLUDED.win_rate,
                    decision=EXCLUDED.decision,
                    status=EXCLUDED.status,
                    maturity_level=EXCLUDED.maturity_level,
                    approved_for_shadow=EXCLUDED.approved_for_shadow,
                    approved_for_paper=EXCLUDED.approved_for_paper,
                    approved_for_live=EXCLUDED.approved_for_live,
                    payload=EXCLUDED.payload,
                    updated_at=now()
            """)
            changed = cur.rowcount
            conn.commit()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.experiment_registry_v1")
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT status, count(*) AS cnt
                FROM warehouse.experiment_registry_v1
                GROUP BY status
                ORDER BY status
            """)
            statuses = cur.fetchall()

    print("=== EXPERIMENT_REGISTRY_BUILDER_V1 ===")
    print(f"registry_rows_changed={changed}")
    print(f"experiment_registry_total={total}")
    for r in statuses:
        print(f"status_count={r['status']}:{r['cnt']}")
    print("политика_источника=RESEARCH_TO_REGISTRY")
    print("реестр=EXPERIMENT_REGISTRY_V1")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("VERDICT=EXPERIMENT_REGISTRY_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
