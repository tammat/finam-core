from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_SYMBOL = "IMOEX"
TARGET_SYMBOL = "IMOEX2"
SOURCE_VERSION = "FORWARD_EDGE_IMOEX2_EXPANSION_V1"
NAMESPACE = uuid.UUID("aa01261e-c2bb-4ce3-a09c-44f1bc8b1523")
MOSCOW = ZoneInfo("Europe/Moscow")


def candidate_identity(row: dict[str, object]) -> tuple[uuid.UUID, str]:
    identity = {
        "source_candidate_id": str(row["incubator_candidate_id"]),
        "source_symbol": SOURCE_SYMBOL,
        "target_symbol": TARGET_SYMBOL,
        "timeframe": row["timeframe"],
        "parameters": row["frozen_parameter_json"],
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return uuid.uuid5(NAMESPACE, canonical), hashlib.sha256(canonical.encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    activated_at = datetime.now(MOSCOW)

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT analytics.forward_edge_baseline_cohort_id_v1() AS cohort_id")
            baseline = cur.fetchone()
            if not baseline or not baseline["cohort_id"]:
                raise RuntimeError("forward edge baseline is not frozen")
            cohort_id = baseline["cohort_id"]
            cur.execute(
                """SELECT * FROM analytics.forward_edge_incubator_v1
                   WHERE cohort_id=%s AND symbol=%s AND timeframe='M5'
                   ORDER BY incubator_candidate_id""",
                (cohort_id, SOURCE_SYMBOL),
            )
            candidates = cur.fetchall()
            if not candidates:
                raise RuntimeError("baseline has no IMOEX M5 candidates")

            inserted = 0
            for row in candidates:
                candidate_id, fingerprint = candidate_identity(row)
                if not args.apply:
                    continue
                cur.execute(
                    """INSERT INTO analytics.forward_edge_incubator_v1 (
                           cohort_id,incubator_candidate_id,hypothesis_id,source_trial_id,
                           source_kind,strategy_family,symbol,timeframe,frozen_parameter_json,
                           frozen_fingerprint,source_gross_pf,activated_at,observation_not_before,
                           minimum_observations,minimum_calendar_days,incubator_status,trust_state,
                           paper_state,promotion_allowed,live_allowed,source_version
                       ) VALUES (
                           %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           'ACCUMULATING','PENDING','NOT_ELIGIBLE',false,false,%s
                       ) ON CONFLICT (cohort_id,incubator_candidate_id) DO NOTHING""",
                    (
                        cohort_id,
                        str(candidate_id),
                        row["hypothesis_id"],
                        row["source_trial_id"],
                        "IMOEX2_EXTENDED_SESSION",
                        row["strategy_family"],
                        TARGET_SYMBOL,
                        row["timeframe"],
                        psycopg2.extras.Json(row["frozen_parameter_json"]),
                        fingerprint,
                        row["source_gross_pf"],
                        activated_at,
                        activated_at,
                        row["minimum_observations"],
                        row["minimum_calendar_days"],
                        SOURCE_VERSION,
                    ),
                )
                inserted += cur.rowcount

            if not args.apply:
                conn.rollback()

    print(f"cohort_id={cohort_id}")
    print(f"source_candidates={len(candidates)}")
    print(f"inserted={inserted}")
    print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
    print("historical_observations_imported=0")
    print("paper_allowed=0")
    print("live_allowed=0")
    print("VERDICT=FORWARD_EDGE_IMOEX2_EXPANSION_V1_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
