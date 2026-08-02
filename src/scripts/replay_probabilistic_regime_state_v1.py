from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from finam_core.regime.regime_state_v1 import regime_probabilities_v1, resolve_regime_state_v1


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    stable = pending = None
    pending_count = 0
    updated = 0
    switches = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT id,mx_trend,mx_strength,rvi_regime,rvi_percentile
              FROM analytics.market_regime_context_v1
              WHERE source_version='MARKET_REGIME_CONTEXT_V2'
              ORDER BY context_ts,id""")
            for row in cursor.fetchall():
                probabilities = regime_probabilities_v1(
                    mx_trend=row["mx_trend"], mx_strength=float(row["mx_strength"]),
                    rvi_regime=row["rvi_regime"], rvi_percentile=float(row["rvi_percentile"]),
                )
                state = resolve_regime_state_v1(
                    probabilities=probabilities, previous_stable_family=stable,
                    previous_pending_family=pending, previous_pending_count=pending_count,
                )
                cursor.execute("""UPDATE analytics.market_regime_context_v1 SET
                  trend_probability=%s,range_probability=%s,shock_probability=%s,
                  candidate_family=%s,stable_family=%s,pending_family=%s,pending_count=%s,
                  regime_switched=%s,probability_source_version='REGIME_STATE_V1_REPLAY'
                  WHERE id=%s""", (
                    state.trend_probability,state.range_probability,state.shock_probability,
                    state.candidate_family,state.stable_family,state.pending_family,
                    state.pending_count,state.switched,row["id"],
                ))
                stable, pending, pending_count = state.stable_family, state.pending_family, state.pending_count
                updated += 1
                switches += int(state.switched)
    print(f"contexts_updated={updated} confirmed_switches={switches}")
    print("paper_changed=0 real_changed=0 promotion_allowed=0")
    print("VERDICT=REGIME_STATE_V1_REPLAY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
