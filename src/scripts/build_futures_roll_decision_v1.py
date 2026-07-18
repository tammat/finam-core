from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
POLICY_CODE="FUTURES_AUTONOMY_V1"


def choose_contract(rows: list[dict],policy: dict) -> tuple[dict,dict|None,str]:
    current=rows[0]
    following=rows[1] if len(rows)>1 else None
    if following and int(current["days_to_expiry"])<=int(policy["roll_days_before_expiry"]):
        return current,following,"EXPIRY_WINDOW_ROLL"
    if following and float(current["median_volume"] or 0)>0 and (
        float(following["median_volume"] or 0)/float(current["median_volume"])
        >=float(policy["next_volume_ratio"])
    ):
        return current,following,"LIQUIDITY_CROSSOVER_ROLL"
    return current,current,"KEEP_LIQUID_FRONT"


def main() -> int:
    run_id=uuid.UUID(os.getenv("EDGE_SEARCH_SCENARIO_RUN_ID",str(uuid.uuid4())))
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT policy FROM analytics.futures_autonomy_policy_v1 WHERE policy_code=%s AND active",(POLICY_CODE,))
            row=cursor.fetchone()
            if not row: raise RuntimeError("FUTURES_AUTONOMY_POLICY_NOT_ACTIVE")
            policy=dict(row["policy"])
            decisions=[]
            for root in policy["roots"]:
                cursor.execute("""WITH latest AS (
                    SELECT max(ts) AS ts FROM public.market_bars WHERE timeframe='M5'
                ) SELECT c.symbol,c.expiration_date,(c.expiration_date-current_date) days_to_expiry,
                    count(b.*) bars,coalesce(percentile_cont(0.5) WITHIN GROUP(ORDER BY b.volume)
                      FILTER(WHERE b.ts>=(SELECT ts FROM latest)-(%s*interval '1 day')),0) median_volume
                  FROM public.futures_contract_calendar c
                  JOIN public.market_bars b ON b.symbol=c.symbol AND b.timeframe='M5'
                    AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')
                  WHERE c.root_symbol=%s AND c.expiration_date>=current_date
                  GROUP BY c.symbol,c.expiration_date
                  HAVING count(b.*)>=%s ORDER BY c.expiration_date,c.symbol""",
                  (int(policy["volume_window_days"]),root,int(policy["minimum_bars"])))
                candidates=[dict(item) for item in cursor.fetchall()]
                if not candidates: raise RuntimeError(f"NO_ROLL_ELIGIBLE_CONTRACT:{root}")
                current,selected,code=choose_contract(candidates,policy)
                next_item=candidates[1] if len(candidates)>1 else None
                cursor.execute("""INSERT INTO analytics.futures_roll_decision_v1
                  (run_id,policy_code,root_symbol,current_symbol,next_symbol,selected_symbol,
                   current_expiration,next_expiration,days_to_expiry,current_median_volume,
                   next_median_volume,decision_code,candidates)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                  ON CONFLICT(run_id,root_symbol) DO UPDATE SET selected_symbol=EXCLUDED.selected_symbol,
                   decision_code=EXCLUDED.decision_code,candidates=EXCLUDED.candidates""",
                  (str(run_id),POLICY_CODE,root,current["symbol"],next_item["symbol"] if next_item else None,
                   selected["symbol"],current["expiration_date"],next_item["expiration_date"] if next_item else None,
                   current["days_to_expiry"],current["median_volume"],
                   next_item["median_volume"] if next_item else 0,code,json.dumps(candidates,default=str)))
                decisions.append((root,selected["symbol"],code))
    print(f"roll_run_id={run_id}")
    for root,symbol,code in decisions: print(f"roll_decision={root}|{symbol}|{code}")
    print("live_allowed=0")
    print("VERDICT=FUTURES_ROLL_DECISION_V1_OK")
    return 0


if __name__=="__main__": raise SystemExit(main())
