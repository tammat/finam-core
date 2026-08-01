from __future__ import annotations

import json
import math
import os
import random
import statistics
import uuid
from collections import defaultdict
from datetime import date

import psycopg2
import psycopg2.extras


DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
BOOTSTRAP_SAMPLES=max(200,min(5000,int(os.getenv("STAT_BOOTSTRAP_SAMPLES","1000"))))
MAX_GROUPS=max(1,min(200,int(os.getenv("STAT_MAX_GROUPS","100"))))
MAX_TRADES=max(20,min(2000,int(os.getenv("STAT_MAX_TRADES_PER_GROUP","500"))))


def quantile(values: list[float], q: float) -> float:
    ordered=sorted(values)
    if not ordered: return 0.0
    return ordered[min(len(ordered)-1,max(0,int(q*(len(ordered)-1))))]


def moving_block_bootstrap(values: list[float], *, samples: int=1000, seed: int=42) -> dict:
    """Preserve local serial dependence instead of iid resampling trades."""
    if not values: return {"ci_low":0.0,"ci_high":0.0,"probability_positive":0.0,"block_length":0}
    n=len(values); block=max(1,min(n,int(round(math.sqrt(n)))))
    rng=random.Random(seed); means=[]
    starts=list(range(max(1,n-block+1)))
    for _ in range(samples):
        sample=[]
        while len(sample)<n:
            start=rng.choice(starts); sample.extend(values[start:start+block])
        means.append(statistics.fmean(sample[:n]))
    return {"ci_low":quantile(means,.025),"ci_high":quantile(means,.975),
            "probability_positive":sum(value>0 for value in means)/len(means),
            "block_length":block}


def minimum_detectable_sample(values: list[float]) -> int | None:
    """Two-sided 5% alpha, 80% power for the observed positive net effect."""
    if len(values)<2: return None
    effect=statistics.fmean(values)
    if effect<=0: return None
    sigma=statistics.stdev(values)
    if sigma<=0: return len(values)
    return min(10000,max(len(values),math.ceil(((1.96+.84)*sigma/effect)**2)))


def concentration(values: list[float], days: list[date]) -> dict:
    positive=sorted((value for value in values if value>0),reverse=True)
    top_trade=positive[0]/sum(positive) if positive and sum(positive)>0 else 1.0
    by_day=defaultdict(float)
    for day,value in zip(days,values): by_day[day]+=value
    positive_days=sorted((value for value in by_day.values() if value>0),reverse=True)
    top_day=positive_days[0]/sum(positive_days) if positive_days and sum(positive_days)>0 else 1.0
    total=sum(values); n=len(values)
    leave_one=[(total-value)/(n-1) for value in values] if n>1 else [values[0]]
    return {"top_trade_share":top_trade,"top_day_share":top_day,
            "leave_one_out_min_expectancy":min(leave_one),
            "pass":top_trade<=.35 and top_day<=.50 and min(leave_one)>0}


def survival_summary(holds: list[int], reasons: list[str]) -> dict:
    """Empirical survival and competing exit risks; censored rows are not mixed in."""
    horizons=(15,30,60,120,240,480)
    survival={str(minutes):sum(seconds>minutes*60 for seconds in holds)/len(holds)
              for minutes in horizons} if holds else {str(minutes):0.0 for minutes in horizons}
    categories=defaultdict(int)
    for reason in reasons:
        code=str(reason or "").lower()
        bucket=("TARGET" if "take" in code or "target" in code else
                "STOP" if "stop" in code else
                "TIME" if "time" in code or "hold" in code else
                "REGIME" if "regime" in code else "OTHER")
        categories[bucket]+=1
    return {"median_hold_seconds":int(statistics.median(holds)) if holds else 0,
            "survival_probability":survival,"exit_competing_risks":dict(categories)}


def cusum_degradation(values: list[float]) -> dict:
    """Negative Page-Hinkley style warning; it never promotes a strategy."""
    if len(values)<20: return {"status":"INSUFFICIENT_SAMPLE","score":0.0}
    baseline=values[:max(10,len(values)//2)]
    mean=statistics.fmean(baseline); sigma=max(statistics.pstdev(baseline),1e-9)
    cumulative=0.0; worst=0.0
    for value in values[len(baseline):]:
        cumulative=min(0.0,cumulative+(value-mean)/sigma+.10)
        worst=min(worst,cumulative)
    score=abs(worst)
    return {"status":"DEGRADATION_ALERT" if score>=5 else "STABLE","score":score,
            "baseline_expectancy":mean,
            "recent_expectancy":statistics.fmean(values[-max(5,len(values)//4):])}


def verdict(*, trades: int, bootstrap: dict, mde: int | None, concentration_result: dict,
            cusum: dict) -> tuple[str,str]:
    if trades<10: return "OBSERVE","SAMPLE_BELOW_10"
    if cusum["status"]=="DEGRADATION_ALERT": return "SHADOW_ONLY","CUSUM_DEGRADATION_ALERT"
    if bootstrap["probability_positive"]<.80: return "OBSERVE","BOOTSTRAP_UNCERTAIN"
    if not concentration_result["pass"]: return "OBSERVE","PROFIT_CONCENTRATED"
    if mde is None or trades<mde: return "ACCUMULATE","MDE_SAMPLE_NOT_REACHED"
    if bootstrap["probability_positive"]>=.95: return "READY_FOR_EXPENSIVE_GATES","LIGHTWEIGHT_GATES_PASS"
    return "ACCUMULATE","BOOTSTRAP_BELOW_95"


def main() -> int:
    run_id=str(uuid.uuid4())
    with psycopg2.connect(DB) as connection:
      with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(941903133) locked")
        if not cursor.fetchone()["locked"]:
            print("VERDICT=LIGHTWEIGHT_STATISTICS_ALREADY_RUNNING"); return 0
        cursor.execute("""SELECT symbol,side,strategy,coalesce(entry_regime,regime,'UNKNOWN') regime,
             net_pnl,coalesce(holding_seconds,hold_seconds::int,0) holding_seconds,
             coalesce(payload->'context'->>'actual_exit_reason','UNKNOWN') exit_reason,
             coalesce(closed_at,exit_ts,created_at) closed_at
          FROM analytics.closed_trades_fresh_v5_confirmed
          WHERE trade_source='paper' AND net_pnl IS NOT NULL
          ORDER BY coalesce(closed_at,exit_ts,created_at)""")
        groups=defaultdict(list)
        for row in cursor.fetchall():
            key=(row["symbol"],row["side"],row["strategy"],row["regime"])
            groups[key].append(dict(row))
        ordered=sorted(groups.items(),key=lambda item:(-len(item[1]),item[0]))[:MAX_GROUPS]
        cursor.execute("INSERT INTO analytics.lightweight_statistical_run_v1(run_id,status_code,groups_total) VALUES(%s,'RUNNING',%s)",(run_id,len(ordered)))
        ready=alerts=0
        for index,(key,rows) in enumerate(ordered):
            rows=rows[-MAX_TRADES:]; values=[float(row["net_pnl"]) for row in rows]
            days=[row["closed_at"].date() for row in rows]
            holds=[int(row["holding_seconds"] or 0) for row in rows]
            reasons=[str(row["exit_reason"]) for row in rows]
            boot=moving_block_bootstrap(values,samples=BOOTSTRAP_SAMPLES,seed=42+index)
            needed=minimum_detectable_sample(values); conc=concentration(values,days)
            survival=survival_summary(holds,reasons); drift=cusum_degradation(values)
            decision,reason=verdict(trades=len(values),bootstrap=boot,mde=needed,
                                    concentration_result=conc,cusum=drift)
            ready+=decision=="READY_FOR_EXPENSIVE_GATES"; alerts+=drift["status"]=="DEGRADATION_ALERT"
            cursor.execute("""INSERT INTO analytics.lightweight_statistical_evidence_v1(
              run_id,symbol,side_code,strategy_code,regime_code,trades,net_pnl,expectancy,
              bootstrap_ci_low,bootstrap_ci_high,probability_positive,block_length,
              mde_required_trades,mde_remaining_trades,top_trade_profit_share,top_day_profit_share,
              leave_one_out_min_expectancy,median_hold_seconds,survival_summary,cusum_status,cusum_score,
              verdict_code,reason_code)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
              (run_id,*key,len(values),sum(values),statistics.fmean(values),boot["ci_low"],boot["ci_high"],
               boot["probability_positive"],boot["block_length"],needed,
               max(0,needed-len(values)) if needed else None,conc["top_trade_share"],conc["top_day_share"],
               conc["leave_one_out_min_expectancy"],survival["median_hold_seconds"],
               psycopg2.extras.Json(survival),drift["status"],drift["score"],decision,reason))
        cursor.execute("""UPDATE analytics.lightweight_statistical_run_v1 SET status_code='COMPLETE',
          ready_for_expensive_gates=%s,degradation_alerts=%s,finished_at=clock_timestamp() WHERE run_id=%s""",
          (ready,alerts,run_id))
    print(f"groups={len(ordered)} ready_for_expensive_gates={ready} degradation_alerts={alerts}")
    print("VERDICT=LIGHTWEIGHT_STATISTICAL_EVIDENCE_V1_OK")
    return 0


if __name__=="__main__": raise SystemExit(main())
