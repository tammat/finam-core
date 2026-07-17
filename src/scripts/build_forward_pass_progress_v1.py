from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ratio(value: Decimal | int, target: Decimal | int) -> Decimal:
    return min(Decimal("1"), Decimal(str(value or 0)) / Decimal(str(target)))


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT g.* FROM analytics.forward_edge_regime_promotion_gate_v1 g
                JOIN analytics.forward_edge_incubator_v1 i USING(cohort_id,incubator_candidate_id)
                WHERE g.cohort_id=analytics.forward_edge_baseline_cohort_id_v1()
                  AND i.incubator_status IN ('ACCUMULATING','ROUTER_REQUIRED')""")
            gates = [dict(row) for row in cur.fetchall()]
            readiness = []
            for gate in gates:
                evidence = Decimal("50") * ratio(gate["closed_observations"], 30) + Decimal("50") * ratio(gate["calendar_days"], 90)
                regime = Decimal("100") * min(
                    ratio(gate["attribution_coverage"], Decimal("0.95")),
                    ratio(gate["tested_regimes"], 2),
                    ratio(gate["positive_regime_share"], Decimal("0.60")),
                )
                financial = Decimal("100") if Decimal(gate["variant_net_pnl"] or 0) > 0 else Decimal("0")
                overall = evidence * Decimal("0.45") + regime * Decimal("0.40") + financial * Decimal("0.15")
                readiness.append((gate, evidence, regime, overall))
            readiness.sort(key=lambda item: (item[0]["decision_code"] != "READY_FOR_PAPER_REVIEW", -item[3], -item[1]))
            cur.execute("TRUNCATE analytics.forward_pass_readiness_v1")
            for rank, (gate, evidence, regime, overall) in enumerate(readiness, 1):
                cur.execute("""INSERT INTO analytics.forward_pass_readiness_v1 VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())""",
                    (gate["cohort_id"],gate["incubator_candidate_id"],gate["policy_code"],gate["closed_observations"],
                     gate["calendar_days"],gate["attribution_coverage"],gate["tested_regimes"],gate["positive_regime_share"],
                     gate["variant_net_pnl"],evidence,regime,overall,rank,gate["decision_code"],
                     psycopg2.extras.Json(gate["reason_codes"]),gate["updated_at"]))

            total=len(readiness); blockers=sum(1 for item in readiness if item[0]["decision_code"]=="HOLD_RESEARCH")
            best_evidence=max((item[1] for item in readiness),default=Decimal("0")); best_regime=max((item[2] for item in readiness),default=Decimal("0"))
            forward_pass=sum(1 for item in readiness if item[0]["decision_code"]=="READY_FOR_PAPER_REVIEW")
            cur.execute("SELECT count(*) count FROM analytics.forward_remediation_scenario_v1 WHERE status_code IN ('WAITING_FUTURE_DATA','ACTIVE')")
            scenarios=cur.fetchone()["count"]
            cur.execute("SELECT count(*) count FROM analytics.forward_pass_shadow_candidate_v1")
            shadow=cur.fetchone()["count"]
            cur.execute("SELECT count(*) count FROM analytics.forward_pass_paper_candidate_v1 WHERE paper_allowed")
            paper=cur.fetchone()["count"]
            rows=(
                (1,"BLOCKER_ANALYSIS","COMPLETE" if total else "WAITING",100 if total else 0,blockers,"BLOCKERS_ANALYZED" if total else "NO_GATE_DATA",{"candidates":total,"blocked":blockers}),
                (2,"FORWARD_EVIDENCE","COMPLETE" if best_evidence>=100 else "IN_PROGRESS",best_evidence,total,"FORWARD_SAMPLE_READY" if best_evidence>=100 else "FORWARD_SAMPLE_ACCUMULATING",{"required_closed":30,"required_days":90}),
                (3,"REGIME_QUALITY","COMPLETE" if best_regime>=100 else "IN_PROGRESS",best_regime,total,"REGIME_QUALITY_READY" if best_regime>=100 else "REGIME_EVIDENCE_ACCUMULATING",{"required_coverage":0.95,"required_regimes":2,"required_positive_share":0.60}),
                (4,"CANDIDATE_PRIORITY","COMPLETE" if total else "WAITING",100 if total else 0,total,"CANDIDATES_RANKED" if total else "NO_CANDIDATES",{"ranked":total}),
                (5,"FUTURE_REMEDIATION","COMPLETE" if scenarios else "WAITING",100 if scenarios else 0,scenarios,"FUTURE_ONLY_SCENARIOS_STORED" if scenarios else "AWAITING_SCENARIOS",{"selection_uses_final_holdout":False}),
                (6,"END_TO_END","COMPLETE" if forward_pass and shadow else "WAITING",100 if forward_pass and shadow else 0,paper,"PIPELINE_VERIFIED" if forward_pass and shadow else "AWAITING_FORWARD_PASS",{"forward_pass":forward_pass,"shadow":shadow,"paper":paper}),
            )
            for row in rows:
                cur.execute("""INSERT INTO analytics.forward_pass_stage_status_v1
                    (step_order,step_code,status_code,progress_pct,item_count,reason_code,evidence,source_as_of,updated_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,clock_timestamp(),clock_timestamp())
                    ON CONFLICT(step_order) DO UPDATE SET step_code=EXCLUDED.step_code,status_code=EXCLUDED.status_code,
                    progress_pct=EXCLUDED.progress_pct,item_count=EXCLUDED.item_count,reason_code=EXCLUDED.reason_code,
                    evidence=EXCLUDED.evidence,source_as_of=EXCLUDED.source_as_of,updated_at=EXCLUDED.updated_at""",
                    (*row[:6], psycopg2.extras.Json(row[6]), *row[7:]))
    print(f"candidates={len(readiness)}")
    print("VERDICT=FORWARD_PASS_PROGRESS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
