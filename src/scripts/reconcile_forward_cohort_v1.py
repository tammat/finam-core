from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_COHORT_RECONCILIATION_V1"


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT analytics.forward_edge_baseline_cohort_id_v1() cohort_id")
            cohort_id = cur.fetchone()["cohort_id"]
            cur.execute("""SELECT i.incubator_candidate_id,i.incubator_status,i.symbol,i.timeframe,
                       max(b.ts) latest_bar,
                       (i.incubator_status IN ('ACCUMULATING','ROUTER_REQUIRED')
                        AND max(b.ts)>=clock_timestamp()-interval '7 days') eligible
                FROM analytics.forward_edge_incubator_v1 i
                LEFT JOIN public.market_bars b ON b.symbol=i.symbol AND b.timeframe=i.timeframe
                WHERE i.cohort_id=%s
                GROUP BY i.incubator_candidate_id,i.incubator_status,i.symbol,i.timeframe""", (cohort_id,))
            candidates = [dict(row) for row in cur.fetchall()]
            eligible = [row for row in candidates if row["eligible"]]
            stale = [row for row in candidates if row["latest_bar"] is None or not row["eligible"]]
            if not candidates:
                status, reason = "BLOCKED", "NO_FORWARD_COHORT_CANDIDATES"
            elif not eligible:
                status, reason = "BLOCKED", "NO_ELIGIBLE_FORWARD_CANDIDATES"
            else:
                status, reason = "HEALTHY", "FORWARD_COHORT_READY"
            evidence = {"stale_symbols": sorted({row["symbol"] for row in stale}), "freshness_limit_days": 7}
            cur.execute("""INSERT INTO analytics.forward_cohort_health_v1
                (health_key,cohort_id,candidate_count,eligible_candidate_count,stale_candidate_count,
                 status_code,reason_code,evidence,source_version,checked_at)
                VALUES('CURRENT',%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())
                ON CONFLICT(health_key) DO UPDATE SET cohort_id=EXCLUDED.cohort_id,
                candidate_count=EXCLUDED.candidate_count,eligible_candidate_count=EXCLUDED.eligible_candidate_count,
                stale_candidate_count=EXCLUDED.stale_candidate_count,status_code=EXCLUDED.status_code,
                reason_code=EXCLUDED.reason_code,evidence=EXCLUDED.evidence,
                source_version=EXCLUDED.source_version,checked_at=EXCLUDED.checked_at""",
                (cohort_id,len(candidates),len(eligible),len(stale),status,reason,
                 psycopg2.extras.Json(evidence),SOURCE_VERSION))
            if not eligible:
                cur.execute("TRUNCATE analytics.forward_pass_readiness_v1")
                stage_rows = (
                    (1,"BLOCKER_ANALYSIS","COMPLETE",100,1,reason),
                    (2,"FORWARD_EVIDENCE","BLOCKED",0,0,reason),
                    (3,"REGIME_QUALITY","BLOCKED",0,0,reason),
                    (4,"CANDIDATE_PRIORITY","BLOCKED",0,0,reason),
                    (5,"FUTURE_REMEDIATION","WAITING",0,0,"AWAITING_VALID_FORWARD_COHORT"),
                    (6,"END_TO_END","WAITING",0,0,"AWAITING_FORWARD_PASS"),
                )
                for row in stage_rows:
                    cur.execute("""INSERT INTO analytics.forward_pass_stage_status_v1
                        (step_order,step_code,status_code,progress_pct,item_count,reason_code,evidence,source_as_of,updated_at)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp(),clock_timestamp())
                        ON CONFLICT(step_order) DO UPDATE SET step_code=EXCLUDED.step_code,status_code=EXCLUDED.status_code,
                        progress_pct=EXCLUDED.progress_pct,item_count=EXCLUDED.item_count,reason_code=EXCLUDED.reason_code,
                        evidence=EXCLUDED.evidence,source_as_of=EXCLUDED.source_as_of,updated_at=EXCLUDED.updated_at""",
                        (*row, psycopg2.extras.Json(evidence)))
    print(f"cohort_id={cohort_id}")
    print(f"eligible_candidates={len(eligible)}")
    print(f"VERDICT={reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
