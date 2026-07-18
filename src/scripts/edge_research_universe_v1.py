from __future__ import annotations

from collections import defaultdict
from typing import Any

POLICY_CODE="DIVERSE_RESEARCH_UNIVERSE_V1"


def category(symbol: str) -> str:
    base=symbol.split("@",1)[0]
    if base.startswith("BR"): return "OIL"
    if base.startswith("NG"): return "GAS"
    if base.startswith(("GD","GL","SV")) or base == "PLZL": return "METALS"
    if "RUB" in base or base.startswith(("USD","CNY")): return "FX"
    if base in {"IMOEX","IMOEX2","RTSI"}: return "INDEX"
    if symbol.endswith("@MISX"): return "EQUITY"
    return "OTHER"


def select_diverse(candidates: list[dict[str,Any]], policy: dict[str,Any]) -> list[dict[str,Any]]:
    quotas={key:int(value) for key,value in policy["category_quotas"].items()}
    maximum=int(policy["max_markets"])
    grouped=defaultdict(list)
    for item in candidates:
        grouped[item["category_code"]].append(item)
    selected=[]
    selected_symbols=set()
    for category_code in policy["category_order"]:
        for item in grouped.get(category_code,[])[:quotas.get(category_code,0)]:
            selected.append(item); selected_symbols.add(item["symbol"])
    for item in candidates:
        if len(selected)>=maximum: break
        if item["symbol"] not in selected_symbols:
            selected.append(item); selected_symbols.add(item["symbol"])
    return selected[:maximum]


def load_research_universe(cursor, *, run_id: str, stage_code: str, min_bars: int,
                           freshness_minutes: int, target_symbol: str="") -> list[dict[str,Any]]:
    cursor.execute("""SELECT policy FROM analytics.edge_research_universe_policy_v1
        WHERE policy_code=%s AND active""",(POLICY_CODE,))
    row=cursor.fetchone()
    if not row:
        raise RuntimeError("EDGE_RESEARCH_UNIVERSE_POLICY_NOT_ACTIVE")
    policy=row["policy"]
    quotas={key:int(value) for key,value in policy["category_quotas"].items()}
    cursor.execute("""SELECT DISTINCT ON(root_symbol) root_symbol,selected_symbol
        FROM analytics.futures_roll_decision_v1 ORDER BY root_symbol,created_at DESC""")
    roll_selection={item["root_symbol"]:item["selected_symbol"] for item in cursor.fetchall()}
    cursor.execute("""
      SELECT b.symbol,b.timeframe,count(*) AS bars,max(b.ts) AS latest_ts,
             coalesce(c.root_symbol,u.root_symbol) AS contract_root,
             coalesce(c.expiration_date,u.expiration_date) AS expiration_date
      FROM public.market_bars b
      LEFT JOIN public.futures_contract_calendar c ON c.symbol=b.symbol
      LEFT JOIN public.futures_contract_universe u ON u.contract_symbol=b.symbol
      WHERE b.timeframe='M5' AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')
        AND (%s='' OR b.symbol=%s)
        AND (b.symbol NOT LIKE '%%@RTSX' OR
             coalesce(c.expiration_date,u.expiration_date)>=current_date)
      GROUP BY b.symbol,b.timeframe,c.root_symbol,u.root_symbol,c.expiration_date,u.expiration_date
      HAVING count(*) >= %s AND max(b.ts)>=clock_timestamp()-(%s * interval '1 minute')
      ORDER BY count(*) DESC,b.symbol
    """,(target_symbol,target_symbol,min_bars,freshness_minutes))
    candidates=[dict(item) for item in cursor.fetchall()]
    cursor.execute("""SELECT symbol,inclusion_mode,priority_override
        FROM analytics.edge_research_universe_override_v1 WHERE active""")
    overrides={str(item["symbol"]):dict(item) for item in cursor.fetchall()}
    cursor.execute("""WITH latest AS (SELECT run_id FROM analytics.instrument_scout_run_v1
        WHERE status_code='COMPLETE' ORDER BY started_at DESC LIMIT 1)
      SELECT r.run_id,r.symbol FROM analytics.instrument_scout_result_v1 r
      WHERE r.run_id=(SELECT run_id FROM latest) AND r.decision_code='SELECTED'""")
    scout_rows=cursor.fetchall()
    scout_run_id=scout_rows[0]["run_id"] if scout_rows else None
    scout_selected={str(item["symbol"]) for item in scout_rows}
    for rank,item in enumerate(candidates,1):
        item["category_code"]=category(item["symbol"])
        item["overall_rank"]=rank
        item["roll_eligible"]=(target_symbol or not item["contract_root"] or
            item["contract_root"] not in roll_selection or
            roll_selection[item["contract_root"]]==item["symbol"])
        item["override"]=overrides.get(item["symbol"],{})
        item["scout_selected"]=item["symbol"] in scout_selected
    eligible=[item for item in candidates if item["roll_eligible"] and item["override"].get("inclusion_mode") != "FORCE_EXCLUDE"]
    eligible.sort(key=lambda item: (not item["scout_selected"],-(item["override"].get("priority_override") or 0),item["overall_rank"]))
    operator_forced=[item for item in eligible if item["override"].get("inclusion_mode") == "FORCE_INCLUDE"]
    forced=operator_forced+[item for item in eligible if item["scout_selected"] and item not in operator_forced]
    forced_counts=defaultdict(int)
    for item in forced: forced_counts[item["category_code"]]+=1
    adjusted_policy=dict(policy)
    adjusted_policy["max_markets"]=max(0,int(policy["max_markets"])-len(forced))
    adjusted_policy["category_quotas"]={key:max(0,int(value)-forced_counts[key]) for key,value in quotas.items()}
    selected=forced[:int(policy["max_markets"])]
    if len(selected)<int(policy["max_markets"]):
        selected.extend(select_diverse([item for item in eligible if item not in forced],adjusted_policy))
    selected_symbols={item["symbol"] for item in selected}
    category_rank=defaultdict(int)
    eligible_category_rank=defaultdict(int)
    cursor.execute("DELETE FROM analytics.edge_research_universe_snapshot_v1 WHERE run_id=%s AND stage_code=%s",(run_id,stage_code))
    for item in candidates:
        code=item["category_code"]; category_rank[code]+=1
        if item["roll_eligible"]: eligible_category_rank[code]+=1
        quota=quotas.get(code,0)
        chosen=item["symbol"] in selected_symbols
        reason=("OPERATOR_FORCE_EXCLUDED" if item["override"].get("inclusion_mode")=="FORCE_EXCLUDE" else
                "OPERATOR_FORCE_INCLUDED" if chosen and item["override"].get("inclusion_mode")=="FORCE_INCLUDE" else
                "AUTONOMOUS_SCOUT_SELECTED" if chosen and item["scout_selected"] else
                "OPERATOR_PRIORITY_SELECTED" if chosen and item["override"].get("priority_override") else
                "ROLLOVER_CONTRACT_NOT_SELECTED" if not item["roll_eligible"] else
                "CATEGORY_QUOTA_SELECTED" if chosen and eligible_category_rank[code]<=quota else
                "GLOBAL_FILL_SELECTED" if chosen else "CATEGORY_QUOTA_EXCEEDED")
        cursor.execute("""INSERT INTO analytics.edge_research_universe_snapshot_v1
          (run_id,stage_code,policy_code,symbol,timeframe,category_code,bars,latest_ts,
           category_rank,overall_rank,selected,reason_code,contract_root,expiration_date)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (run_id,stage_code,POLICY_CODE,item["symbol"],item["timeframe"],code,item["bars"],
           item["latest_ts"],category_rank[code],item["overall_rank"],chosen,reason,
           item["contract_root"],item["expiration_date"]))
    if scout_run_id:
        cursor.execute("""WITH unlocked AS (
            SELECT queue_id FROM analytics.instrument_scout_queue_v1
            WHERE run_id=%s AND symbol=ANY(%s) AND status_code='PENDING'
            FOR UPDATE SKIP LOCKED)
          UPDATE analytics.instrument_scout_queue_v1 q SET status_code='APPLIED',updated_at=clock_timestamp(),
            evidence=evidence||jsonb_build_object('applied_run_id',%s::text,'applied_stage',%s)
          FROM unlocked u WHERE q.queue_id=u.queue_id""",
          (scout_run_id,list(selected_symbols),run_id,stage_code))
    return selected
