from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
EPOCH = "POST_FIX_V1"
NAMESPACE = uuid.UUID("00a90f71-cee2-4b7c-92ea-2a3a8ab6f451")

# These are prospective expert policies.  They collect genuinely future
# observations; no historical score is represented as an OOS pass.
BRANCHES = (
    dict(code="SBER_LONG_M5_POST_FIX_V1", logical="SBER@MISX", observation="SBER@MISX",
         strategy="MEAN_REVERSION_EQUITY", side="LONG", candidate="EXPERT_EQUITY_RANGE_RETEST",
         entry="ADAPTIVE", stop=1.3, take=1.6, trail_after=1.0, trail=0.8, embargo=14400),
    dict(code="BRQ6_SHORT_M5_POST_FIX_V1", logical="BRQ6@RTSX", observation="BRQ6@RTSX",
         strategy="BR_CONSERVATIVE_BREAKOUT", side="SHORT", candidate="EXPERT_BR_RETEST_VOLUME",
         entry="ADAPTIVE", stop=1.6, take=2.6, trail_after=1.2, trail=1.0, embargo=21600),
    dict(code="GLDRUBF_LONG_M5_POST_FIX_V1", logical="GLDRUBF@RTSX", observation="GDU6@RTSX",
         strategy="GOLD_TREND_BREAKOUT", side="LONG", candidate="EXPERT_GOLD_CONFIRM_MTF",
         entry="ADAPTIVE", stop=1.7, take=2.7, trail_after=1.2, trail=1.0, embargo=21600),
    dict(code="CNYRUBF_LONG_M5_POST_FIX_V1", logical="CNYRUBF@RTSX", observation="CNYRUBF@RTSX",
         strategy="CNY_REGIME_FUTURES", side="LONG", candidate="EXPERT_FX_RETEST_COST",
         entry="ADAPTIVE", stop=1.4, take=2.0, trail_after=1.0, trail=0.9, embargo=21600),
)


def _id(kind: str, code: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{code}")


def register(cur, frozen_at: datetime) -> int:
    cur.execute("""SELECT run_id FROM analytics.trade_outcome_pattern_run_v1
                   ORDER BY source_max_closed_at DESC NULLS LAST,created_at DESC LIMIT 1""")
    source = cur.fetchone()
    if not source:
        raise RuntimeError("No trade_outcome_pattern_run_v1 source run")
    inserted = 0
    for branch in BRANCHES:
        hypothesis_id = _id("hypothesis", branch["code"])
        admission_id = _id("admission", branch["code"])
        confirmation_after = frozen_at + timedelta(seconds=branch["embargo"])
        evidence = {
            "methodology_epoch": EPOCH,
            "prospective_only": True,
            "historical_result_is_not_oos_pass": True,
            "branch_code": branch["code"],
        }
        cur.execute("""INSERT INTO analytics.trade_outcome_hypothesis_v1(
            hypothesis_id,hypothesis_key,source_run_id,hypothesis_type,strategy_code,
            side_code,session_code,holding_code,trades,context_complete_trades,
            profit_factor,expectancy,priority_score,lifecycle_state,recommendation_code,
            evidence,regime_code,symbol)
          VALUES(%s,%s,%s,'FILTER_OOS_CANDIDATE',%s,%s,'*','*',0,0,0,0,1000,
                 'READY_FOR_OOS','FREEZE_FOR_FUTURE_OOS',%s,'*',%s)
          ON CONFLICT(hypothesis_key) DO NOTHING""",
          (str(hypothesis_id), branch["code"], source["run_id"], branch["strategy"],
           branch["side"], psycopg2.extras.Json(evidence), branch["logical"]))
        request = {
            "source": "V5_POST_FIX_BRANCH_REGISTRY_V1",
            "methodology_epoch": EPOCH,
            "branch_code": branch["code"],
            "paper_strategy_code": branch["strategy"],
            "strategy_code": branch["strategy"],
            "timeframe": "M5",
            "side_code": branch["side"],
            "symbol": branch["logical"],
            "observation_symbol": branch["observation"],
            "session_code": "*", "holding_code": "*", "regime_code": "*",
            "observation_source": "ENTRY_EXIT_SHADOW_V2",
            "minimum_closed_trades": 20,
            "promotion_allowed": False, "paper_allowed": False, "real_trading_allowed": False,
            "frozen_profile": {
                "candidate_code": branch["candidate"], "entry_mode": branch["entry"],
                "stop_atr": branch["stop"], "take_atr": branch["take"],
                "trail_after_r": branch["trail_after"], "trail_atr": branch["trail"],
            },
            "temporal_isolation": {
                "policy": "PURGED_EMBARGO_V5_V1", "future_data_only": True,
                "purge_before_ts": frozen_at.isoformat(),
                "embargo_seconds": branch["embargo"],
                "confirmation_after_ts": confirmation_after.isoformat(),
            },
        }
        cur.execute("""INSERT INTO analytics.trade_outcome_oos_admission_v1(
            admission_id,hypothesis_id,symbol,fresh_closed_trades,context_complete_trades,
            microstructure_coverage_ratio,required_microstructure_coverage,status_code,
            reason_code,oos_request,net_expectancy,net_profit_factor,execution_cost,cost_admission_status)
          VALUES(%s,%s,%s,0,0,0,0,'QUEUED','POST_FIX_V1_WAITING_FUTURE_OBSERVATIONS',
                 %s,NULL,NULL,0,'PROSPECTIVE_ONLY')
          ON CONFLICT(admission_id) DO NOTHING""",
          (str(admission_id), str(hypothesis_id), branch["logical"],
           psycopg2.extras.Json(request)))
        cur.execute("""INSERT INTO analytics.v5_post_fix_branch_registry_v1(
            branch_code,methodology_epoch,logical_symbol,observation_symbol,strategy_code,
            side_code,timeframe,candidate_code,entry_mode,stop_atr,take_atr,trail_after_r,
            trail_atr,frozen_at,admission_id,metadata)
          VALUES(%s,%s,%s,%s,%s,%s,'M5',%s,%s,%s,%s,%s,%s,%s,%s,%s)
          ON CONFLICT(branch_code) DO NOTHING""",
          (branch["code"], EPOCH, branch["logical"], branch["observation"],
           branch["strategy"], branch["side"], branch["candidate"], branch["entry"],
           branch["stop"], branch["take"], branch["trail_after"], branch["trail"],
           frozen_at, str(admission_id), psycopg2.extras.Json(evidence)))
        inserted += int(cur.rowcount or 0)
    return inserted


def main() -> int:
    frozen_at = datetime.now(timezone.utc)
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            count = register(cur, frozen_at)
    print(f"branches_registered={count}")
    print("paper_allowed=0 real_allowed=0")
    print("VERDICT=V5_POST_FIX_BRANCH_REGISTRY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
