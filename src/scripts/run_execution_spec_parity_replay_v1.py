from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

from finam_core.analytics.entry_exit_optimizer import candidate_policy_code
from finam_core.research.execution_spec_v1 import (
    build_execution_spec, compare_specs, execution_spec_hash,
)


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def _spec(row: dict, profile: dict) -> dict:
    return build_execution_spec(
        symbol=row["observation_symbol"], strategy=row["strategy_code"],
        side=row["side_code"], timeframe=row["timeframe"], profile=profile,
        policy_code=candidate_policy_code(profile["candidate_code"]),
    )


def main() -> int:
    checked = matched = mismatched = not_proven = 0
    with psycopg2.connect(DB) as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('execution_spec_parity_replay_v1'))")
        cur.execute("""SELECT r.*,a.oos_request FROM analytics.v5_post_fix_branch_registry_v1 r
                       JOIN analytics.trade_outcome_oos_admission_v1 a USING(admission_id)
                       ORDER BY r.branch_code""")
        for row in map(dict, cur.fetchall()):
            frozen = dict((row["oos_request"] or {}).get("frozen_profile") or {})
            research = _spec(row, frozen)
            cur.execute("""SELECT * FROM analytics.entry_exit_runtime_profile_v1
                           WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                             AND candidate_code=%s AND execution_mode='paper'
                             AND (status='ACTIVE' OR activated_by='PARITY_STAGED_V1')
                           ORDER BY (status='ACTIVE') DESC,activated_at DESC LIMIT 1""", (
                row["strategy_code"],
                "BR" if row["strategy_code"] == "BR_CONSERVATIVE_BREAKOUT" else
                "GOLD" if row["strategy_code"] == "GOLD_TREND_BREAKOUT" else
                "CNY" if row["strategy_code"] == "CNY_REGIME_FUTURES" else
                row["observation_symbol"].split("@", 1)[0],
                row["side_code"], frozen["candidate_code"],
            ))
            runtime_row = cur.fetchone()
            runtime = None
            profile_id = None
            if runtime_row:
                runtime_row = dict(runtime_row)
                profile_id = runtime_row["profile_id"]
                runtime = _spec(row, runtime_row)
            verdict, reasons = compare_specs(research, runtime or {})
            cur.execute("""DELETE FROM analytics.execution_spec_parity_v1
                           WHERE admission_id=%s AND profile_id IS NOT DISTINCT FROM %s
                             AND source_signal_id IS NULL""", (row["admission_id"], profile_id))
            cur.execute("""INSERT INTO analytics.execution_spec_parity_v1(
                  admission_id,profile_id,research_spec,research_spec_hash,runtime_spec,
                  runtime_spec_hash,verdict_code,reason_codes)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                row["admission_id"], profile_id, psycopg2.extras.Json(research),
                execution_spec_hash(research), psycopg2.extras.Json(runtime) if runtime else None,
                execution_spec_hash(runtime) if runtime else None, verdict,
                psycopg2.extras.Json(reasons),
            ))
            checked += 1
            matched += verdict == "MATCH"
            mismatched += verdict == "MISMATCH"
            not_proven += verdict == "NOT_PROVEN"
    print(f"checked={checked} match={matched} mismatch={mismatched} not_proven={not_proven}")
    print("VERDICT=EXECUTION_SPEC_PARITY_REPLAY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
