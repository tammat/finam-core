from __future__ import annotations

import json
import os
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "research" / "forward_edge_promotion_policy_v1.json"
MIGRATION = ROOT / "sql" / "analytics" / "048_forward_edge_regime_promotion_gate_v1.sql"
SOURCE_VERSION = "FORWARD_EDGE_REGIME_PROMOTION_GATE_V1"


def dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def evaluate(summary: dict[str, Any], policy: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    checks = (
        (summary["closed"] >= int(policy["minimum_closed_observations"]), "INSUFFICIENT_CLOSED_OBSERVATIONS"),
        (summary["calendar_days"] >= int(policy["minimum_calendar_days"]), "INSUFFICIENT_CALENDAR_DAYS"),
        (summary["coverage"] >= dec(policy["minimum_attribution_coverage"]), "INSUFFICIENT_REGIME_COVERAGE"),
        (summary["tested_regimes"] >= int(policy["minimum_tested_regimes"]), "INSUFFICIENT_TESTED_REGIMES"),
        (summary["positive_share"] >= dec(policy["minimum_positive_regime_share"]), "LOW_POSITIVE_REGIME_SHARE"),
        (summary["variant_net"] > dec(policy["minimum_total_net_pnl"]), "NON_POSITIVE_TOTAL_NET_PNL"),
    )
    reasons.extend(reason for passed, reason in checks if not passed)
    if policy["require_positive_regime_net_pnl"] and summary["nonpositive_regimes"]:
        reasons.append("NON_POSITIVE_ELIGIBLE_REGIME")
    if policy["require_nonnegative_regime_delta"] and summary["negative_delta_regimes"]:
        reasons.append("NEGATIVE_DELTA_ELIGIBLE_REGIME")
    return not reasons, reasons


def main() -> int:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(MIGRATION.read_text(encoding="utf-8"))
            cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                print("VERDICT=FORWARD_EDGE_REGIME_PROMOTION_GATE_V1_NO_COHORT")
                return 0
            cohort_id = latest["cohort_id"]
            cur.execute("""
                WITH policies AS (
                    SELECT DISTINCT policy_code
                    FROM analytics.forward_edge_shadow_exit_variant_v1
                    WHERE cohort_id=%s
                )
                SELECT
                    i.incubator_candidate_id,i.strategy_family,i.minimum_observations,i.minimum_calendar_days,
                    p.policy_code,o.observation_id,o.entry_ts,o.exit_ts,o.observation_status,
                    o.net_pnl AS baseline_net_pnl,v.variant_status,v.net_pnl AS variant_net_pnl,
                    COALESCE(r.regime,'UNKNOWN') AS regime_code
                FROM analytics.forward_edge_incubator_v1 i
                CROSS JOIN policies p
                LEFT JOIN analytics.forward_edge_observation_v1 o
                  USING (cohort_id,incubator_candidate_id)
                LEFT JOIN analytics.forward_edge_shadow_exit_variant_v1 v
                  ON v.observation_id=o.observation_id AND v.policy_code=p.policy_code
                LEFT JOIN LATERAL (
                    SELECT s.regime
                    FROM analytics_regime_snapshots_v2 s
                    WHERE s.symbol=o.symbol AND s.timeframe=o.timeframe
                      AND s.ts<=o.entry_ts AND s.ts>=o.entry_ts-interval '15 minutes'
                    ORDER BY s.ts DESC LIMIT 1
                ) r ON true
                WHERE i.cohort_id=%s
                ORDER BY i.incubator_candidate_id,v.policy_code,o.entry_ts
            """, (cohort_id, cohort_id))
            grouped: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
            for row in cur.fetchall():
                grouped[(row["incubator_candidate_id"], row["policy_code"])].append(dict(row))

            ready = held = 0
            for (candidate_id, policy_code), rows in grouped.items():
                closed = [r for r in rows if r["variant_status"] == "CLOSED"]
                dated = [r for r in rows if r["entry_ts"] is not None]
                calendar_days = 0 if not dated else (max(r["entry_ts"] for r in dated).date() - min(r["entry_ts"] for r in dated).date()).days + 1
                attributed = [r for r in closed if r["regime_code"] != "UNKNOWN"]
                coverage = Decimal(len(attributed)) / Decimal(len(closed)) if closed else Decimal("0")
                regimes: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for row in attributed:
                    regimes[row["regime_code"]].append(row)
                eligible = {code: values for code, values in regimes.items() if len(values) >= int(policy["minimum_closed_per_regime"])}
                regime_metrics = {
                    code: (
                        sum((dec(row["variant_net_pnl"]) for row in values), Decimal("0")),
                        sum((dec(row["baseline_net_pnl"]) for row in values), Decimal("0")),
                    )
                    for code, values in eligible.items()
                }
                positive = sum(1 for variant, _ in regime_metrics.values() if variant > 0)
                tested = len(regime_metrics)
                positive_share = Decimal(positive) / Decimal(tested) if tested else Decimal("0")
                variant_net = sum((dec(r["variant_net_pnl"]) for r in closed), Decimal("0"))
                baseline_net = sum((dec(r["baseline_net_pnl"]) for r in closed), Decimal("0"))
                summary = {
                    "closed": len(closed), "calendar_days": calendar_days, "coverage": coverage,
                    "tested_regimes": tested, "positive_share": positive_share, "variant_net": variant_net,
                    "nonpositive_regimes": [code for code, (variant, _) in regime_metrics.items() if variant <= 0],
                    "negative_delta_regimes": [code for code, (variant, baseline) in regime_metrics.items() if variant < baseline],
                }
                candidate_policy = dict(policy)
                candidate_policy["minimum_closed_observations"] = max(
                    int(policy["minimum_closed_observations"]), int(rows[0]["minimum_observations"])
                )
                candidate_policy["minimum_calendar_days"] = max(
                    int(policy["minimum_calendar_days"]), int(rows[0]["minimum_calendar_days"])
                )
                review_eligible, reasons = evaluate(summary, candidate_policy)
                decision = policy["decision_on_pass"] if review_eligible else policy["decision_on_fail"]
                ready += int(review_eligible)
                held += int(not review_eligible)
                cur.execute("""
                    INSERT INTO analytics.forward_edge_regime_promotion_gate_v1 (
                        cohort_id,incubator_candidate_id,policy_code,strategy_family,closed_observations,
                        calendar_days,attributed_closed,attribution_coverage,tested_regimes,positive_regimes,
                        positive_regime_share,variant_net_pnl,baseline_net_pnl,net_pnl_delta,decision_code,
                        reason_codes,review_eligible,promotion_allowed,live_allowed,policy_version,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,false,false,%s,%s)
                    ON CONFLICT (cohort_id,incubator_candidate_id,policy_code) DO UPDATE SET
                        closed_observations=excluded.closed_observations,calendar_days=excluded.calendar_days,
                        attributed_closed=excluded.attributed_closed,attribution_coverage=excluded.attribution_coverage,
                        tested_regimes=excluded.tested_regimes,positive_regimes=excluded.positive_regimes,
                        positive_regime_share=excluded.positive_regime_share,variant_net_pnl=excluded.variant_net_pnl,
                        baseline_net_pnl=excluded.baseline_net_pnl,net_pnl_delta=excluded.net_pnl_delta,
                        decision_code=excluded.decision_code,reason_codes=excluded.reason_codes,
                        review_eligible=excluded.review_eligible,promotion_allowed=false,live_allowed=false,
                        policy_version=excluded.policy_version,source_version=excluded.source_version,updated_at=now()
                """, (
                    cohort_id,candidate_id,policy_code,rows[0]["strategy_family"],len(closed),calendar_days,
                    len(attributed),coverage,tested,positive,positive_share,variant_net,baseline_net,
                    variant_net-baseline_net,decision,json.dumps(reasons),review_eligible,
                    policy["contract_version"],SOURCE_VERSION,
                ))

    print(f"cohort_id={cohort_id}")
    print(f"candidates_evaluated={len(grouped)}")
    print(f"ready_for_paper_review={ready}")
    print(f"hold_research={held}")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=FORWARD_EDGE_REGIME_PROMOTION_GATE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
