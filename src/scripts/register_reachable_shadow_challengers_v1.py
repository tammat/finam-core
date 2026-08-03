from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "REACHABLE_SHADOW_CHALLENGERS_V1"

# These candidates address observed reachability/entry-timing failures.  Their
# historical diagnostics are rationale only and are never reused as prospective
# evidence.  Registration starts a clean future-only clock.
CHALLENGERS = (
    ("SBER_LONG_REACHABLE_V1", "SBER_LONG_M5_POST_FIX_V1", "MEAN_REVERSION_EQUITY",
     "SBER@MISX", "LONG", "IMMEDIATE_S1.5_R1.6", "reachable_cost_aware_control"),
    ("BRQ6_SHORT_REACHABLE_V1", "BRQ6_SHORT_M5_POST_FIX_V1", "BR_CONSERVATIVE_BREAKOUT",
     "BRQ6@RTSX", "SHORT", "RETEST_3_S1.5_R1.6", "avoid_immediate_gap_entry"),
    ("GLDRUBF_LONG_REACHABLE_V1", "GLDRUBF_LONG_M5_POST_FIX_V1", "GOLD_TREND_BREAKOUT",
     "GDU6@RTSX", "LONG", "ADAPTIVE_S2.3_R2.4", "adaptive_wide_geometry"),
    ("CNYRUBF_LONG_REACHABLE_V1", "CNYRUBF_LONG_M5_POST_FIX_V1", "CNY_REGIME_FUTURES",
     "CNYRUBF@RTSX", "LONG", "ADAPTIVE_S2.3_R2.4", "cost_aware_adaptive_entry"),
)


def register(cursor, *, frozen_at: datetime) -> int:
    inserted = 0
    for code, parent, strategy, symbol, side, candidate, rationale in CHALLENGERS:
        evidence = {
            "source_version": SOURCE_VERSION,
            "prospective_only": True,
            "historical_diagnostics_reused": False,
            "rationale": rationale,
            "paper_allowed": False,
            "real_allowed": False,
        }
        cursor.execute(
            """INSERT INTO analytics.reachable_shadow_challenger_v1(
                 challenger_code,parent_branch_code,strategy_code,observation_symbol,
                 side_code,candidate_code,frozen_at,evidence)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
               ON CONFLICT(challenger_code) DO NOTHING""",
            (code, parent, strategy, symbol, side, candidate, frozen_at, json.dumps(evidence)),
        )
        inserted += int(cursor.rowcount or 0)
    return inserted


def main() -> int:
    frozen_at = datetime.now(timezone.utc)
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        inserted = register(cursor, frozen_at=frozen_at)
    print(f"challengers_inserted={inserted}")
    print("historical_results_reused=0 paper_allowed=0 real_allowed=0")
    print(f"VERDICT={SOURCE_VERSION}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
