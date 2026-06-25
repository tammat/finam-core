#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHADOW_RUNTIME_QUEUE_ENGINE_V1

Идемпотентная очередь передачи кандидатов из Research Layer в Shadow Runtime.

Источник истины:
- research.global_edge_forensic_reports_v1
- research.oos_validation_campaigns_v1
- research.oos_validation_decisions_v1

Важно:
- Runtime не меняется.
- Execution не меняется.
- Micro Live не разрешается.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_table(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS research")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS research.shadow_runtime_queue_v1 (
            queue_id BIGSERIAL PRIMARY KEY,
            candidate_id TEXT NOT NULL UNIQUE,
            forensic_report_id BIGINT NOT NULL,
            campaign_id BIGINT NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            priority INTEGER NOT NULL,
            queue_status TEXT NOT NULL,
            queue_reason TEXT NOT NULL,
            runtime_changed BOOLEAN NOT NULL DEFAULT false,
            execution_changed BOOLEAN NOT NULL DEFAULT false,
            micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shadow_runtime_queue_status_priority_v1
        ON research.shadow_runtime_queue_v1(queue_status, priority DESC)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shadow_runtime_queue_symbol_strategy_v1
        ON research.shadow_runtime_queue_v1(symbol, strategy, timeframe)
        """
    )


def upsert_queue(cur) -> int:
    ensure_table(cur)

    cur.execute(
        """
        WITH latest_forensic AS (
            SELECT DISTINCT ON (candidate_id)
                report_id AS forensic_report_id,
                candidate_id,
                symbol,
                strategy,
                timeframe,
                recommendation,
                replay_status,
                forensic_status,
                robustness_status,
                runtime_changed,
                micro_live_allowed,
                created_at
            FROM research.global_edge_forensic_reports_v1
            ORDER BY candidate_id, created_at DESC
        ),
        latest_oos AS (
            SELECT DISTINCT ON (c.candidate_id)
                c.candidate_id,
                c.campaign_id,
                d.decision,
                d.decision_reason,
                d.runtime_changed AS oos_runtime_changed,
                d.micro_live_allowed AS oos_micro_live_allowed,
                d.created_at
            FROM research.oos_validation_campaigns_v1 c
            JOIN research.oos_validation_decisions_v1 d
              ON d.campaign_id = c.campaign_id
            ORDER BY c.candidate_id, d.created_at DESC
        ),
        candidates AS (
            SELECT
                f.candidate_id,
                f.forensic_report_id,
                o.campaign_id,
                f.symbol,
                f.strategy,
                f.timeframe,
                100::integer AS priority,
                CASE
                    WHEN o.decision = 'PASS_TO_SHADOW'
                     AND f.recommendation = 'PROMOTE_TO_OOS_VALIDATION'
                     AND f.replay_status = 'PASS'
                     AND f.robustness_status = 'PASS'
                     AND f.runtime_changed = false
                     AND f.micro_live_allowed = false
                     AND o.oos_runtime_changed = false
                     AND o.oos_micro_live_allowed = false
                    THEN 'READY'
                    WHEN o.decision IS NULL
                    THEN 'WAITING'
                    ELSE 'BLOCKED'
                END AS queue_status,
                CASE
                    WHEN o.decision = 'PASS_TO_SHADOW'
                     AND f.recommendation = 'PROMOTE_TO_OOS_VALIDATION'
                     AND f.replay_status = 'PASS'
                     AND f.robustness_status = 'PASS'
                     AND f.runtime_changed = false
                     AND f.micro_live_allowed = false
                     AND o.oos_runtime_changed = false
                     AND o.oos_micro_live_allowed = false
                    THEN 'PASS_TO_SHADOW'
                    WHEN o.decision IS NULL
                    THEN 'WAITING_FOR_OOS_DECISION'
                    ELSE coalesce(o.decision_reason, 'OOS_NOT_PASS_TO_SHADOW')
                END AS queue_reason,
                jsonb_build_object(
                    'source', 'SHADOW_RUNTIME_QUEUE_ENGINE_V1',
                    'forensic_recommendation', f.recommendation,
                    'replay_status', f.replay_status,
                    'forensic_status', f.forensic_status,
                    'robustness_status', f.robustness_status,
                    'oos_decision', o.decision,
                    'oos_decision_reason', o.decision_reason,
                    'runtime_changed', false,
                    'execution_changed', false,
                    'micro_live_allowed', false
                ) AS payload
            FROM latest_forensic f
            LEFT JOIN latest_oos o
              ON o.candidate_id = f.candidate_id
        )
        INSERT INTO research.shadow_runtime_queue_v1 (
            candidate_id,
            forensic_report_id,
            campaign_id,
            symbol,
            strategy,
            timeframe,
            priority,
            queue_status,
            queue_reason,
            runtime_changed,
            execution_changed,
            micro_live_allowed,
            payload,
            updated_at
        )
        SELECT
            candidate_id,
            forensic_report_id,
            campaign_id,
            symbol,
            strategy,
            timeframe,
            priority,
            queue_status,
            queue_reason,
            false,
            false,
            false,
            payload,
            now()
        FROM candidates
        WHERE campaign_id IS NOT NULL
        ON CONFLICT (candidate_id)
        DO UPDATE SET
            forensic_report_id = EXCLUDED.forensic_report_id,
            campaign_id = EXCLUDED.campaign_id,
            symbol = EXCLUDED.symbol,
            strategy = EXCLUDED.strategy,
            timeframe = EXCLUDED.timeframe,
            priority = EXCLUDED.priority,
            queue_status = EXCLUDED.queue_status,
            queue_reason = EXCLUDED.queue_reason,
            runtime_changed = false,
            execution_changed = false,
            micro_live_allowed = false,
            payload = EXCLUDED.payload,
            updated_at = now()
        """
    )
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                changed_rows = upsert_queue(cur)
                conn.commit()
            else:
                ensure_table(cur)
                conn.rollback()
                changed_rows = 0

            cur.execute(
                """
                SELECT
                    count(*)::bigint AS rows_total,
                    sum(CASE WHEN queue_status='READY' THEN 1 ELSE 0 END)::bigint AS ready_rows,
                    sum(CASE WHEN queue_status='WAITING' THEN 1 ELSE 0 END)::bigint AS waiting_rows,
                    sum(CASE WHEN queue_status='BLOCKED' THEN 1 ELSE 0 END)::bigint AS blocked_rows,
                    count(*) - count(DISTINCT candidate_id) AS duplicate_candidates
                FROM research.shadow_runtime_queue_v1
                """
            )
            summary = dict(cur.fetchone())

            cur.execute(
                """
                SELECT
                    candidate_id,
                    symbol,
                    strategy,
                    timeframe,
                    priority,
                    queue_status,
                    queue_reason,
                    runtime_changed,
                    execution_changed,
                    micro_live_allowed
                FROM research.shadow_runtime_queue_v1
                ORDER BY priority DESC, updated_at DESC
                """
            )
            rows = [dict(r) for r in cur.fetchall()]

    print("=== SHADOW_RUNTIME_QUEUE_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"changed_rows={changed_rows}")
    print(f"rows_total={summary['rows_total']}")
    print(f"ready_rows={summary['ready_rows']}")
    print(f"waiting_rows={summary['waiting_rows']}")
    print(f"blocked_rows={summary['blocked_rows']}")
    print(f"duplicate_candidates={summary['duplicate_candidates']}")

    for r in rows:
        print(
            "queue="
            f"{r['candidate_id']}|"
            f"{r['symbol']}|"
            f"{r['strategy']}|"
            f"{r['timeframe']}|"
            f"priority={r['priority']}|"
            f"status={r['queue_status']}|"
            f"reason={r['queue_reason']}|"
            f"runtime_changed={r['runtime_changed']}|"
            f"execution_changed={r['execution_changed']}|"
            f"micro_live_allowed={r['micro_live_allowed']}"
        )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SHADOW_RUNTIME_QUEUE_ENGINE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
