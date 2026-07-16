from __future__ import annotations

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
PROXY_SYMBOL = "MXU6@RTSX"
SOURCE_VERSION = "FORWARD_EDGE_MX_PROXY_COHORT_V1"
MOSCOW = ZoneInfo("Europe/Moscow")
NAMESPACE = uuid.UUID("de12b3c0-ea39-4a9c-aeda-49c24a22dc95")


def proxy_symbol(symbol: str) -> str:
    return PROXY_SYMBOL if symbol == SOURCE_SYMBOL else symbol


def main() -> int:
    activated_at = datetime.now(MOSCOW)
    cohort_id = uuid.uuid4()
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                raise RuntimeError("No source forward-edge cohort")
            source_cohort_id = latest["cohort_id"]
            cur.execute(
                "SELECT * FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s ORDER BY incubator_candidate_id",
                (source_cohort_id,),
            )
            candidates = cur.fetchall()
            if any(row["symbol"] == PROXY_SYMBOL for row in candidates) and not any(
                row["symbol"] == SOURCE_SYMBOL for row in candidates
            ):
                print(f"cohort_id={source_cohort_id}")
                print("VERDICT=FORWARD_EDGE_MX_PROXY_COHORT_V1_ALREADY_ACTIVE")
                return 0

            proxied = 0
            for row in candidates:
                symbol = proxy_symbol(str(row["symbol"]))
                proxied += int(symbol == PROXY_SYMBOL)
                identity = {
                    "source_candidate_id": str(row["incubator_candidate_id"]),
                    "source_cohort_id": str(source_cohort_id),
                    "execution_proxy": symbol,
                    "parameters": row["frozen_parameter_json"],
                }
                canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
                candidate_id = uuid.uuid5(NAMESPACE, canonical)
                fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
                cur.execute("""
                    INSERT INTO analytics.forward_edge_incubator_v1 (
                        cohort_id,incubator_candidate_id,hypothesis_id,source_trial_id,source_kind,
                        strategy_family,symbol,timeframe,frozen_parameter_json,frozen_fingerprint,
                        source_gross_pf,activated_at,observation_not_before,minimum_observations,
                        minimum_calendar_days,incubator_status,trust_state,paper_state,
                        promotion_allowed,live_allowed,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s)
                """, (
                    str(cohort_id),str(candidate_id),str(row["hypothesis_id"]),
                    str(row["source_trial_id"]) if row["source_trial_id"] else None,
                    "MX_EXECUTION_PROXY" if symbol == PROXY_SYMBOL else row["source_kind"],
                    row["strategy_family"],symbol,row["timeframe"],
                    psycopg2.extras.Json(row["frozen_parameter_json"]),fingerprint,
                    row["source_gross_pf"],activated_at,activated_at,row["minimum_observations"],
                    row["minimum_calendar_days"],
                    "ACCUMULATING" if symbol == PROXY_SYMBOL else row["incubator_status"],
                    "PENDING","NOT_ELIGIBLE",SOURCE_VERSION,
                ))

    print(f"source_cohort_id={source_cohort_id}")
    print(f"cohort_id={cohort_id}")
    print(f"candidates={len(candidates)}")
    print(f"proxied_candidates={proxied}")
    print(f"observation_not_before={activated_at.isoformat(timespec='seconds')}")
    print("historical_observations_imported=0")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=FORWARD_EDGE_MX_PROXY_COHORT_V1_CREATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
