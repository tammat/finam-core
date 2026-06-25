#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


def db():
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure(cur):
    cur.execute("""
    CREATE SCHEMA IF NOT EXISTS research;

    CREATE TABLE IF NOT EXISTS research.shadow_runtime_scorecard_v1
    (
        scorecard_id BIGSERIAL PRIMARY KEY,

        shadow_run_id BIGINT NOT NULL UNIQUE,

        candidate_id TEXT NOT NULL,

        symbol TEXT NOT NULL,

        strategy TEXT NOT NULL,

        timeframe TEXT NOT NULL,

        total_events INTEGER NOT NULL,

        planned_events INTEGER NOT NULL,

        starting_events INTEGER NOT NULL,

        running_events INTEGER NOT NULL,

        completed_events INTEGER NOT NULL,

        failed_events INTEGER NOT NULL,

        timeout_events INTEGER NOT NULL,

        cancelled_events INTEGER NOT NULL,

        avg_latency_ms NUMERIC,

        avg_runtime_seconds NUMERIC,

        avg_queue_wait_seconds NUMERIC,

        payload JSONB NOT NULL,

        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)


def build(cur):

    ensure(cur)

    cur.execute("""
    INSERT INTO research.shadow_runtime_scorecard_v1
    (
        shadow_run_id,
        candidate_id,
        symbol,
        strategy,
        timeframe,
        total_events,
        planned_events,
        starting_events,
        running_events,
        completed_events,
        failed_events,
        timeout_events,
        cancelled_events,
        avg_latency_ms,
        avg_runtime_seconds,
        avg_queue_wait_seconds,
        payload
    )

    SELECT

        r.shadow_run_id,

        r.candidate_id,

        r.symbol,

        r.strategy,

        r.timeframe,

        count(m.*),

        sum(case when m.transition_from='PLANNED' then 1 else 0 end),

        sum(case when m.transition_to='STARTING' then 1 else 0 end),

        sum(case when m.transition_to='RUNNING' then 1 else 0 end),

        sum(case when m.transition_to='COMPLETED' then 1 else 0 end),

        sum(case when m.transition_to='FAILED' then 1 else 0 end),

        sum(case when m.transition_to='TIMEOUT' then 1 else 0 end),

        sum(case when m.transition_to='CANCELLED' then 1 else 0 end),

        avg(m.latency_ms),

        avg(m.runtime_seconds),

        avg(m.queue_wait_seconds),

        jsonb_build_object(

            'source',

            'SHADOW_RUNTIME_SCORECARD_ENGINE_V1',

            'aggregation',

            'PER_SHADOW_RUN',

            'runtime_changed',

            false,

            'execution_changed',

            false,

            'orders_changed',

            false,

            'fills_changed',

            false,

            'micro_live_allowed',

            false

        )

    FROM research.shadow_runtime_runs_v1 r

    JOIN research.shadow_runtime_monitor_v1 m

      ON m.shadow_run_id=r.shadow_run_id

    GROUP BY

        r.shadow_run_id,

        r.candidate_id,

        r.symbol,

        r.strategy,

        r.timeframe

    ON CONFLICT (shadow_run_id)

    DO UPDATE SET

        total_events=EXCLUDED.total_events,

        planned_events=EXCLUDED.planned_events,

        starting_events=EXCLUDED.starting_events,

        running_events=EXCLUDED.running_events,

        completed_events=EXCLUDED.completed_events,

        failed_events=EXCLUDED.failed_events,

        timeout_events=EXCLUDED.timeout_events,

        cancelled_events=EXCLUDED.cancelled_events,

        avg_latency_ms=EXCLUDED.avg_latency_ms,

        avg_runtime_seconds=EXCLUDED.avg_runtime_seconds,

        avg_queue_wait_seconds=EXCLUDED.avg_queue_wait_seconds,

        payload=EXCLUDED.payload;
    """)

    return cur.rowcount


def main():

    parser=argparse.ArgumentParser()

    parser.add_argument("--save",action="store_true")

    args=parser.parse_args()

    with psycopg2.connect(db()) as conn:

        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            if args.save:

                rows=build(cur)

                conn.commit()

            else:

                ensure(cur)

                conn.rollback()

                rows=0

            cur.execute("""

            SELECT

                count(*) scorecards,

                sum(total_events) total_events,

                sum(starting_events) starting_events

            FROM research.shadow_runtime_scorecard_v1

            """)

            s=dict(cur.fetchone())

            cur.execute("""

            SELECT

                candidate_id,

                symbol,

                strategy,

                timeframe,

                total_events,

                starting_events

            FROM research.shadow_runtime_scorecard_v1

            ORDER BY created_at DESC

            LIMIT 1

            """)

            last=dict(cur.fetchone())

    print("=== SHADOW_RUNTIME_SCORECARD_ENGINE_V1 ===")

    print(f"mode={'save' if args.save else 'dry_run'}")

    print(f"changed_rows={rows}")

    print(f"scorecards={s['scorecards']}")

    print(f"total_events={s['total_events']}")

    print(f"starting_events={s['starting_events']}")

    print(
        "scorecard="
        f"{last['candidate_id']}|"
        f"{last['symbol']}|"
        f"{last['strategy']}|"
        f"{last['timeframe']}|"
        f"events={last['total_events']}|"
        f"starting={last['starting_events']}"
    )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print("VERDICT=SHADOW_RUNTIME_SCORECARD_ENGINE_V1_READY")

    return 0


if __name__=="__main__":

    sys.exit(main())
