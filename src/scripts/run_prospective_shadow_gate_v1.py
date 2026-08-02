from __future__ import annotations

import os
import uuid
from collections import Counter
from datetime import timedelta
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
NAMESPACE = uuid.UUID("272ef639-0bd8-4c33-af53-05b3b2aa1f47")
EARLY_MIN = 8
PROMOTION_MIN = 10
FINAL_MIN = 15
MIN_PF = Decimal("1.05")
MAX_TOP_GAIN_SHARE = Decimal("0.60")


def independent(rows: list[dict]) -> list[dict]:
    """Keep non-overlapping labels so correlated holding windows count once."""
    accepted, last_end = [], None
    for row in sorted(rows, key=lambda value: (value["label_start_ts"], value["source_signal_id"])):
        if last_end is None or row["label_start_ts"] >= last_end:
            accepted.append(row)
            last_end = row["label_end_ts"]
    return accepted


def metrics(rows: list[dict]) -> dict:
    values = [Decimal(str(row["shadow_net_r"])) for row in rows]
    gains = [value for value in values if value > 0]
    losses = [-value for value in values if value < 0]
    gross_gain, gross_loss = sum(gains, Decimal(0)), sum(losses, Decimal(0))
    return {
        "n": len(values),
        "days": len({row["label_start_ts"].date() for row in rows}),
        "expectancy": sum(values, Decimal(0)) / len(values) if values else None,
        "pf": gross_gain / gross_loss if gross_loss else (Decimal("999") if gross_gain else None),
        "top_gain_share": max(gains) / gross_gain if gains and gross_gain else None,
        "wins": len(gains),
    }


def decide(value: dict) -> tuple[str, str]:
    if value["n"] < EARLY_MIN:
        return "ACCUMULATING", "PROSPECTIVE_SAMPLE_BELOW_8"
    if value["n"] >= EARLY_MIN and value["expectancy"] <= Decimal("-0.25") and (value["pf"] or 0) < Decimal("0.75"):
        return "EARLY_REJECT", "CLEAR_NEGATIVE_ECONOMICS_AFTER_8"
    ready = (
        value["n"] >= PROMOTION_MIN and value["days"] >= 2
        and value["expectancy"] is not None and value["expectancy"] > 0
        and value["pf"] is not None and value["pf"] >= MIN_PF
        and value["top_gain_share"] is not None and value["top_gain_share"] <= MAX_TOP_GAIN_SHARE
    )
    if ready:
        return "READY_FOR_V5", "PROSPECTIVE_ECONOMIC_AND_DIVERSITY_GATES_PASSED"
    if value["n"] >= FINAL_MIN:
        return "EARLY_REJECT", "PROSPECTIVE_GATE_NOT_PASSED_BY_15"
    return "ACCUMULATING", "PROSPECTIVE_EVIDENCE_INCOMPLETE"


def _promote(cur, branch: dict, last_end, request: dict) -> uuid.UUID:
    admission_id = uuid.uuid5(NAMESPACE, f"oos-after-prospective:{branch['branch_code']}")
    embargo = int(request["temporal_isolation"]["embargo_seconds"])
    confirmation = last_end + timedelta(seconds=embargo)
    promoted = dict(request)
    promoted.update({"phase": "FROZEN_V5_OOS", "prospective_reuse_allowed": False})
    promoted["temporal_isolation"] = {
        "policy": "PURGED_EMBARGO_V5_V1", "future_data_only": True,
        "purge_before_ts": last_end.isoformat(), "embargo_seconds": embargo,
        "confirmation_after_ts": confirmation.isoformat(),
    }
    cur.execute("""INSERT INTO analytics.trade_outcome_oos_admission_v1(
      admission_id,hypothesis_id,symbol,fresh_closed_trades,context_complete_trades,
      microstructure_coverage_ratio,required_microstructure_coverage,status_code,reason_code,
      oos_request,net_expectancy,net_profit_factor,execution_cost,cost_admission_status)
      VALUES(%s,%s,%s,0,0,0,0,'QUEUED','PROSPECTIVE_PASS_NEW_FUTURE_BOUNDARY',%s,NULL,NULL,0,'PROSPECTIVE_PASS')
      ON CONFLICT(admission_id) DO NOTHING""",
      (str(admission_id), branch["hypothesis_id"], branch["logical_symbol"], psycopg2.extras.Json(promoted)))
    return admission_id


def run(cur) -> int:
    cur.execute("""SELECT r.*,a.hypothesis_id,a.oos_request,a.status_code admission_status
      FROM analytics.v5_post_fix_branch_registry_v1 r
      JOIN analytics.trade_outcome_oos_admission_v1 a ON a.admission_id=r.admission_id
      WHERE r.state_code IN ('V5_COLLECTING','OOS_PASS','OOS_FAIL') ORDER BY r.branch_code""")
    branches = [dict(row) for row in cur.fetchall()]
    for branch in branches:
        # Diagnostic only: this funnel must never stop, promote, or reset V5.
        cur.execute("""SELECT source_signal_id,label_start_ts,label_end_ts,shadow_net_r,
          shadow_entered,entry_decision,entry_decision_reason
          FROM analytics.entry_exit_signal_shadow_pair_v2
          WHERE symbol_code=%s AND strategy_code=%s AND side_code=%s AND candidate_code=%s
            AND label_start_ts >= %s ORDER BY label_start_ts,source_signal_id""",
          (branch["observation_symbol"],branch["strategy_code"],branch["side_code"],
           branch["candidate_code"],branch["frozen_at"]))
        rows = [dict(row) for row in cur.fetchall()]
        closed = [row for row in rows if row["shadow_net_r"] is not None]
        unique = independent(closed)
        value = metrics(unique)
        reasons = Counter(str(row["entry_decision_reason"] or "UNKNOWN") for row in rows
                          if str(row["entry_decision"] or "SKIP") == "SKIP")
        dominant, dominant_count = reasons.most_common(1)[0] if reasons else (None, 0)
        now = branch["frozen_at"] if not rows else max(row["label_end_ts"] for row in rows)
        cur.execute("""INSERT INTO analytics.prospective_shadow_funnel_v1 VALUES(
          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
          (branch["branch_code"],now,len({r["source_signal_id"] for r in rows}),len(rows),
           sum(str(r["entry_decision"] or "SKIP") != "SKIP" for r in rows),
           sum(bool(r["shadow_entered"]) for r in rows),len(closed),value["n"],value["wins"],
           dominant,dominant_count))
        decision, reason = decide(value)
        new_admission = None
        payload = {key: (float(item) if isinstance(item, Decimal) else item) for key,item in value.items()}
        cur.execute("""INSERT INTO analytics.prospective_shadow_gate_decision_v1(
          branch_code,evaluated_at,decision_code,reason_code,independent_observations,trading_days,
          expectancy_r,profit_factor,top_gain_share,oos_admission_id,metrics)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
          (branch["branch_code"],now,decision,reason,value["n"],value["days"],value["expectancy"],
           value["pf"],value["top_gain_share"],str(new_admission) if new_admission else None,
           psycopg2.extras.Json(payload)))
    return len(branches)


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(184003) locked")
            if not cur.fetchone()["locked"]:
                print("VERDICT=PROSPECTIVE_SHADOW_GATE_ALREADY_RUNNING")
                return 0
            count = run(cur)
    print(f"branches_evaluated={count}")
    print("gate_mode=DIAGNOSTIC_ONLY paper_allowed=0 real_allowed=0")
    print("VERDICT=PROSPECTIVE_SHADOW_GATE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
