from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections import defaultdict
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE_VERSION="SHADOW_PASS_EVALUATOR_V1"
NAMESPACE=uuid.UUID("95af7b03-1662-48a0-af05-fb154ae83e1e")


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def metrics(rows: list[dict], policy: dict) -> dict:
    closed=[row for row in rows if row["shadow_status"]=="CLOSED" and row["net_pnl"] is not None]
    values=[dec(row["net_pnl"]) for row in closed]
    wins=sum((value for value in values if value>0),Decimal(0))
    losses=abs(sum((value for value in values if value<=0),Decimal(0)))
    pf=(wins/losses if losses else (Decimal("999") if wins else Decimal(0)))
    expectancy=(sum(values,Decimal(0))/len(values) if values else Decimal(0))
    cumulative=peak=max_drawdown=Decimal(0)
    for value in values:
        cumulative+=value; peak=max(peak,cumulative); max_drawdown=max(max_drawdown,peak-cumulative)
    dates=[row["exit_ts"].date() for row in closed if row["exit_ts"]]
    calendar_days=(max(dates)-min(dates)).days+1 if dates else 0
    cost_ready=sum(1 for row in closed if row["commission"] is not None and row["spread_cost"] is not None)
    cost_coverage=Decimal(cost_ready)/len(closed) if closed else Decimal(0)
    regimes=defaultdict(list)
    for row in closed:
        regimes[str(row["regime_code"] or "UNKNOWN")].append(dec(row["net_pnl"]))
    eligible={code:items for code,items in regimes.items()
              if code!="UNKNOWN" and len(items)>=policy["minimum_closed_per_regime"]}
    positive=sum(1 for items in eligible.values() if sum(items,Decimal(0))>0)
    tested=len(eligible)
    positive_share=Decimal(positive)/tested if tested else Decimal(0)
    progress=min(Decimal(100),Decimal(50)*min(Decimal(1),Decimal(len(closed))/policy["minimum_closed"])
                 +Decimal(50)*min(Decimal(1),Decimal(calendar_days)/policy["minimum_calendar_days"]))
    return {"closed_trades":len(closed),"calendar_days":calendar_days,"profit_factor":pf,
            "expectancy":expectancy,"max_drawdown":max_drawdown,"cost_coverage":cost_coverage,
            "tested_regimes":tested,"positive_regimes":positive,"positive_regime_share":positive_share,
            "progress_pct":progress,
            "slippage_coverage":(Decimal(sum(1 for row in closed if row["slippage"] is not None))/len(closed) if closed else Decimal(0))}


def decide(value: dict, policy: dict) -> tuple[str,list[str]]:
    waiting=[]
    if value["closed_trades"]<policy["minimum_closed"]: waiting.append("SHADOW_MINIMUM_TRADES_PENDING")
    if value["calendar_days"]<policy["minimum_calendar_days"]: waiting.append("SHADOW_MINIMUM_DAYS_PENDING")
    if waiting:return "WAIT",waiting
    reasons=[]
    if value["profit_factor"]<policy["minimum_profit_factor"]:reasons.append("SHADOW_PROFIT_FACTOR_BELOW_GATE")
    if value["expectancy"]<=policy["minimum_expectancy"]:reasons.append("SHADOW_EXPECTANCY_NOT_POSITIVE")
    if value["max_drawdown"]>policy["maximum_drawdown"]:reasons.append("SHADOW_DRAWDOWN_ABOVE_LIMIT")
    if value["cost_coverage"]<policy["minimum_cost_coverage"]:reasons.append("SHADOW_COST_COVERAGE_INSUFFICIENT")
    if value["tested_regimes"]<policy["minimum_tested_regimes"]:reasons.append("SHADOW_REGIME_COVERAGE_INSUFFICIENT")
    if value["positive_regime_share"]<policy["minimum_positive_regime_share"]:reasons.append("SHADOW_REGIME_STABILITY_FAILED")
    return ("FAIL",reasons) if reasons else ("PASS",["SHADOW_ALL_GATES_PASSED"])


def main() -> int:
    assessed=passed=paper_created=0
    with psycopg2.connect(DB) as connection:
      with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
        cursor.execute("SELECT * FROM analytics.shadow_pass_policy_v1 WHERE policy_code='SHADOW_PASS_V1' AND enabled")
        policy=cursor.fetchone()
        if not policy:raise RuntimeError("SHADOW_PASS_POLICY_MISSING")
        cursor.execute("SELECT * FROM analytics.forward_pass_shadow_candidate_v1 WHERE candidate_status='ACTIVE' ORDER BY shadow_candidate_id")
        for candidate in cursor.fetchall():
            cursor.execute("""SELECT s.*,o.regime_code FROM analytics.forward_pass_shadow_observation_v1 s
                LEFT JOIN analytics.forward_edge_observation_v1 o ON o.observation_id=s.source_observation_id
                WHERE s.shadow_candidate_id=%s ORDER BY s.exit_ts NULLS LAST,s.signal_ts,s.shadow_observation_id""",
                (candidate["shadow_candidate_id"],))
            value=metrics(cursor.fetchall(),policy)
            decision,reasons=decide(value,policy)
            evidence={**value,"thresholds":{key:policy[key] for key in (
                "minimum_closed","minimum_calendar_days","minimum_profit_factor","minimum_expectancy",
                "maximum_drawdown","minimum_cost_coverage","minimum_tested_regimes","minimum_positive_regime_share")}}
            evidence_json=json.loads(json.dumps(evidence,default=str))
            decision_fp=digest({"candidate":candidate["shadow_candidate_id"],"decision":decision,"reasons":reasons,"evidence":evidence,"version":policy["config_version"]})
            decision_id=uuid.uuid5(NAMESPACE,"decision:"+decision_fp)
            cursor.execute("""INSERT INTO analytics.shadow_pass_decision_v1(
                decision_id,shadow_candidate_id,decision_code,reason_codes,evidence,decision_fingerprint,policy_version)
                VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(decision_fingerprint) DO NOTHING""",
                (str(decision_id),candidate["shadow_candidate_id"],decision,psycopg2.extras.Json(reasons),
                 psycopg2.extras.Json(evidence_json),decision_fp,policy["config_version"]))
            cursor.execute("""INSERT INTO analytics.shadow_pass_status_v1(
                shadow_candidate_id,policy_code,decision_code,reason_codes,closed_trades,calendar_days,
                profit_factor,expectancy,max_drawdown,cost_coverage,tested_regimes,positive_regimes,
                positive_regime_share,progress_pct,evidence,policy_version)
                VALUES(%s,'SHADOW_PASS_V1',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(shadow_candidate_id) DO UPDATE SET decision_code=EXCLUDED.decision_code,
                reason_codes=EXCLUDED.reason_codes,closed_trades=EXCLUDED.closed_trades,
                calendar_days=EXCLUDED.calendar_days,profit_factor=EXCLUDED.profit_factor,
                expectancy=EXCLUDED.expectancy,max_drawdown=EXCLUDED.max_drawdown,
                cost_coverage=EXCLUDED.cost_coverage,tested_regimes=EXCLUDED.tested_regimes,
                positive_regimes=EXCLUDED.positive_regimes,positive_regime_share=EXCLUDED.positive_regime_share,
                progress_pct=EXCLUDED.progress_pct,evidence=EXCLUDED.evidence,
                policy_version=EXCLUDED.policy_version,evaluated_at=clock_timestamp()""",
                (candidate["shadow_candidate_id"],decision,psycopg2.extras.Json(reasons),value["closed_trades"],
                 value["calendar_days"],value["profit_factor"],value["expectancy"],value["max_drawdown"],
                 value["cost_coverage"],value["tested_regimes"],value["positive_regimes"],
                 value["positive_regime_share"],value["progress_pct"],psycopg2.extras.Json(evidence_json),policy["config_version"]))
            assessed+=1;passed+=int(decision=="PASS")
            if decision=="PASS":
                paper_id=uuid.uuid5(NAMESPACE,"paper:"+str(candidate["shadow_candidate_id"]))
                cursor.execute("""INSERT INTO analytics.forward_pass_paper_candidate_v1(
                    paper_candidate_id,shadow_candidate_id,cohort_id,incubator_candidate_id,
                    strategy_family,symbol,timeframe,parameter_json,shadow_decision_id,paper_status,
                    paper_allowed,runtime_allowed,execution_enabled,live_allowed,source_version)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'READY_FOR_PAPER_OBSERVATION',TRUE,FALSE,FALSE,FALSE,%s)
                    ON CONFLICT(shadow_candidate_id) DO UPDATE SET shadow_decision_id=EXCLUDED.shadow_decision_id,
                    paper_allowed=TRUE,runtime_allowed=FALSE,execution_enabled=FALSE,live_allowed=FALSE,
                    updated_at=clock_timestamp()""",
                    (str(paper_id),candidate["shadow_candidate_id"],candidate["cohort_id"],
                     candidate["incubator_candidate_id"],candidate["strategy_family"],candidate["symbol"],
                     candidate["timeframe"],psycopg2.extras.Json(candidate["parameter_json"]),str(decision_id),SOURCE_VERSION))
                paper_created+=int(cursor.rowcount>0)
    print(f"shadow_candidates_assessed={assessed}");print(f"shadow_pass={passed}")
    print(f"paper_candidates_written={paper_created}");print("runtime_allowed=0");print("live_allowed=0")
    print("VERDICT=SHADOW_PASS_EVALUATOR_V1_OK");return 0


if __name__=="__main__":raise SystemExit(main())
