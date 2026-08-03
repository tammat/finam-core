from __future__ import annotations

import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "REACHABLE_SHADOW_CHALLENGER_GATE_V1"


def main() -> int:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_xact_lock(184007)")
        if not cursor.fetchone()[0]:
            print("VERDICT=REACHABLE_SHADOW_CHALLENGER_GATE_ALREADY_RUNNING")
            return 0
        cursor.execute("""WITH decisions AS (
          SELECT challenger_code,prospective_verdict,matched,entered,completed,active_days,
                 expectancy_r,placebo_r,delta_r,gap_stops,latest_result_ts,
                 CASE prospective_verdict
                   WHEN 'READY_FOR_EXPENSIVE_GATES' THEN 'READY_FOR_EXPENSIVE_GATES'
                   WHEN 'EARLY_REJECT' THEN 'EARLY_REJECT'
                   ELSE 'SHADOW_ACCUMULATION'
                 END next_state
          FROM analytics.reachable_shadow_challenger_status_v1
        )
        UPDATE analytics.reachable_shadow_challenger_v1 c
           SET state_code=d.next_state,
               evidence=c.evidence || jsonb_build_object(
                 'latest_gate',jsonb_build_object(
                   'source_version',%s,'verdict',d.prospective_verdict,
                   'matched',d.matched,'entered',d.entered,'completed',d.completed,
                   'active_days',d.active_days,'expectancy_r',d.expectancy_r,
                   'placebo_r',d.placebo_r,'delta_r',d.delta_r,
                   'gap_stops',d.gap_stops,'latest_result_ts',d.latest_result_ts,
                   'evaluated_at',clock_timestamp()),
                 'paper_allowed',false,'real_allowed',false),
               updated_at=clock_timestamp()
          FROM decisions d
         WHERE c.challenger_code=d.challenger_code
           AND c.state_code<>'RETIRED'
        RETURNING c.state_code""", (SOURCE_VERSION,))
        states = [row[0] for row in cursor.fetchall()]
    print(f"challengers_evaluated={len(states)}")
    print(f"ready_for_expensive_gates={states.count('READY_FOR_EXPENSIVE_GATES')}")
    print(f"early_reject={states.count('EARLY_REJECT')}")
    print("paper_allowed=0 real_allowed=0")
    print(f"VERDICT={SOURCE_VERSION}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
