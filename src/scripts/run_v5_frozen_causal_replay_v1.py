from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "V5_FROZEN_CAUSAL_REPLAY_V1"


def diagnostic_verdict(*, source_signals: int, completed: int, entry_rate: float,
                       expectancy_r: float | None, edge_r: float | None) -> tuple[str, str]:
    if source_signals >= 10 and entry_rate < 0.05:
        return "REACHABILITY_FAIL", "ENTRY_RATE_BELOW_5_PERCENT"
    if completed < 5:
        return "INSUFFICIENT_COMPLETED", "FEWER_THAN_5_COMPLETED_OUTCOMES"
    if expectancy_r is None or expectancy_r <= 0:
        return "NEGATIVE_DIAGNOSTIC", "NET_EXPECTANCY_NOT_POSITIVE"
    if edge_r is None or edge_r <= 0:
        return "NO_PLACEBO_EDGE", "DOES_NOT_BEAT_MATCHED_PLACEBO"
    return "PROMISING_DIAGNOSTIC", "POSITIVE_AFTER_COSTS_AND_PLACEBO"


def main() -> int:
    require_off_market_research_window(SOURCE_VERSION)
    replay_run_id = uuid.uuid4()
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT r.branch_code,r.candidate_code,r.observation_symbol,
                r.strategy_code,r.side_code,r.frozen_at,
                greatest(r.frozen_at-interval '30 days',min(p.label_start_ts)) window_start,
                count(p.*) source_signals,
                count(*) FILTER(WHERE p.shadow_entered) entered_signals,
                count(*) FILTER(WHERE p.shadow_net_r IS NOT NULL) completed_outcomes,
                sum(p.shadow_net_r) FILTER(WHERE p.shadow_net_r IS NOT NULL) net_r,
                avg(p.shadow_net_r) FILTER(WHERE p.shadow_net_r IS NOT NULL) expectancy_r,
                avg(p.placebo_net_r) FILTER(WHERE p.shadow_net_r IS NOT NULL) paired_placebo_r
              FROM analytics.v5_post_fix_branch_registry_v1 r
              LEFT JOIN analytics.entry_exit_signal_shadow_pair_v2 p
                ON p.symbol_code=r.observation_symbol AND p.strategy_code=r.strategy_code
               AND p.side_code=r.side_code AND p.candidate_code=r.candidate_code
               AND p.label_end_ts<r.frozen_at
               AND p.label_start_ts>=r.frozen_at-interval '30 days'
              WHERE r.methodology_epoch='POST_FIX_V1'
              GROUP BY r.branch_code,r.candidate_code,r.observation_symbol,
                       r.strategy_code,r.side_code,r.frozen_at
              ORDER BY r.branch_code""")
            rows = cursor.fetchall()
            for row in rows:
                source_signals = int(row["source_signals"] or 0)
                entered = int(row["entered_signals"] or 0)
                completed = int(row["completed_outcomes"] or 0)
                entry_rate = entered / source_signals if source_signals else 0.0
                expectancy = float(row["expectancy_r"]) if row["expectancy_r"] is not None else None
                placebo = float(row["paired_placebo_r"]) if row["paired_placebo_r"] is not None else None
                edge = expectancy - placebo if expectancy is not None and placebo is not None else None
                verdict, reason = diagnostic_verdict(
                    source_signals=source_signals, completed=completed, entry_rate=entry_rate,
                    expectancy_r=expectancy, edge_r=edge,
                )
                cursor.execute("""INSERT INTO analytics.v5_frozen_causal_replay_v1(
                    replay_run_id,branch_code,candidate_code,observation_symbol,side_code,
                    window_start,window_end,source_signals,entered_signals,completed_outcomes,
                    entry_rate,net_r,expectancy_r,paired_placebo_r,edge_over_placebo_r,
                    diagnostic_verdict,reason_code,gate_mode,source_version)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                         'DIAGNOSTIC_ONLY',%s)""", (
                    str(replay_run_id),row["branch_code"],row["candidate_code"],
                    row["observation_symbol"],row["side_code"],
                    row["window_start"] or row["frozen_at"],row["frozen_at"],
                    source_signals,entered,completed,entry_rate,row["net_r"],
                    row["expectancy_r"],row["paired_placebo_r"],edge,verdict,reason,
                    SOURCE_VERSION,
                ))
    print(f"replay_run_id={replay_run_id} branches={len(rows)}")
    print("gate_mode=DIAGNOSTIC_ONLY v5_observations_changed=0 paper_changed=0 real_changed=0")
    print(f"VERDICT={SOURCE_VERSION}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
