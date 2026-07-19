from __future__ import annotations
from zoneinfo import ZoneInfo

def classify_market_session(ts, policies) -> str:
    for policy in sorted(policies,key=lambda item:int(item["priority"]),reverse=True):
        local=ts.astimezone(ZoneInfo(str(policy["timezone_code"])))
        if local.isoweekday() in set(policy["weekdays"]) and policy["local_start"] <= local.time().replace(tzinfo=None) < policy["local_end"]:
            return str(policy["session_code"])
    return "OTHER"

def session_breakdown(trades, policies) -> dict:
    grouped={}
    for trade in trades:
        code=classify_market_session(trade.entry_ts,policies)
        grouped.setdefault(code,[]).append(trade)
    result={}
    for code,items in grouped.items():
        pnls=[float(item.net_pnl) for item in items]
        wins=[value for value in pnls if value>0]; losses=[value for value in pnls if value<=0]
        loss=abs(sum(losses))
        result[code]={"trades":len(items),"net_expectancy":sum(pnls)/len(pnls),
            "net_profit_factor":sum(wins)/loss if loss else (sum(wins) if wins else 0.0)}
    return result
