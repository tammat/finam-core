#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from finam_core.analytics.futures_shadow_promotion import simulate_shadow,promotion_decision
from finam_core.strategy.futures_adaptive_risk_policy import FuturesAdaptiveRiskPolicy
from scripts.analytics.build_futures_risk_calibration_v1 import TIMEFRAMES,atr_at_entry,asset_for

def conn(): return psycopg2.connect(os.environ['DATABASE_URL'])

def main():
  policy=FuturesAdaptiveRiskPolicy()
  with conn() as c,c.cursor(cursor_factory=RealDictCursor) as x:
    x.execute("select pg_advisory_xact_lock(hashtext('futures_shadow_promotion_v1'))")
    x.execute("select distinct on(asset_code,side_code) * from analytics.futures_risk_calibration_v1 order by asset_code,side_code,generated_at desc")
    calibrations={(r['asset_code'],r['side_code']):r for r in x.fetchall()}
    x.execute("""select id,symbol,upper(side) side,entry_price,exit_price,net_pnl,
      coalesce(entry_ts,opened_at,created_at) entry_ts,coalesce(closed_at,exit_ts,created_at) exit_ts
      from closed_trades where symbol like '%%@RTSX' and trade_source='paper'
      and coalesce(payload->'context'->>'cohort','') like 'FRESH_V5%%'
      order by coalesce(entry_ts,opened_at,created_at)""")
    grouped=defaultdict(list)
    for t in x.fetchall():
      asset=asset_for(t['symbol']); side='LONG' if t['side'] in ('LONG','BUY') else 'SHORT'
      if asset: grouped[(asset,side)].append(t)
    for profile in policy.PROFILES:
      for side in ('LONG','SHORT'):
        cal=calibrations.get((profile.asset,side)) or {}
        stop=float(cal.get('recommended_stop_atr') or profile.min_stop_atr)
        take=float(cal.get('recommended_take_atr') or profile.target_atr)
        volume=float(cal.get('recommended_volume_ratio') or profile.min_volume_ratio)
        version=hashlib.sha256(f'{profile.asset}:{side}:{stop:.4f}:{take:.4f}:{volume:.4f}'.encode()).hexdigest()[:16]
        actual_values=[];shadow_values=[]; rows=[]
        trades=grouped.get((profile.asset,side),[])
        for t in trades:
          atr=atr_at_entry(x,t['symbol'],TIMEFRAMES[profile.asset],t['entry_ts'])
          if not atr: continue
          x.execute("select high::float8,low::float8,close::float8 from market_bars where symbol=%s and timeframe=%s and ts between %s and %s order by ts",(t['symbol'],TIMEFRAMES[profile.asset],t['entry_ts'],t['exit_ts']))
          bars=[(r['high'],r['low'],r['close']) for r in x.fetchall()]
          direction=1 if side=='LONG' else -1
          risk=atr*stop
          actual_r=direction*(float(t['exit_price'])-float(t['entry_price']))/risk
          outcome=simulate_shadow(entry_price=float(t['entry_price']),side=side,atr=atr,stop_atr=stop,take_atr=take,bars=bars)
          if not outcome: continue
          actual_values.append(actual_r);shadow_values.append(outcome.net_r);rows.append((t,outcome,actual_r))
        oos=max(0,min(20,len(rows)//5))
        metrics=promotion_decision(actual_values,shadow_values,oos_size=oos)
        for idx,(t,outcome,actual_r) in enumerate(rows):
          x.execute("""insert into analytics.futures_risk_shadow_pair_v1
          (trade_id,asset_code,side_code,candidate_version,entry_ts,exit_ts,actual_net_r,shadow_net_r,shadow_exit_reason,shadow_exit_price,stop_atr,take_atr,is_oos)
          values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
          on conflict(trade_id,candidate_version) do update set actual_net_r=excluded.actual_net_r,shadow_net_r=excluded.shadow_net_r,
          shadow_exit_reason=excluded.shadow_exit_reason,shadow_exit_price=excluded.shadow_exit_price,is_oos=excluded.is_oos,generated_at=clock_timestamp()""",
          (t['id'],profile.asset,side,version,t['entry_ts'],t['exit_ts'],actual_r,outcome.net_r,outcome.exit_reason,outcome.exit_price,stop,take,oos>0 and idx>=len(rows)-oos))
        can_promote=metrics['promote'] and cal.get('recommendation_status')=='CANDIDATE_FOR_REVIEW'
        if can_promote:
          x.execute("update analytics.futures_risk_runtime_profile_v1 set status='SUPERSEDED' where asset_code=%s and side_code=%s and execution_mode='paper' and status='ACTIVE'",(profile.asset,side))
          x.execute("select coalesce(max(version),0)+1 as next_version from analytics.futures_risk_runtime_profile_v1 where asset_code=%s and side_code=%s and execution_mode='paper'",(profile.asset,side)); number=x.fetchone()['next_version']
          x.execute("""insert into analytics.futures_risk_runtime_profile_v1
          (asset_code,side_code,version,status,mode,min_stop_atr,max_stop_atr,target_atr,min_reward_r,min_volume_ratio,source_calibration_date,promotion_metrics,activated_at)
          values(%s,%s,%s,'ACTIVE','ENFORCE',%s,%s,%s,%s,%s,%s,%s::jsonb,clock_timestamp())""",
          (profile.asset,side,number,stop,max(stop,profile.max_stop_atr),take,profile.min_reward_r,volume,cal['calibration_date'],json.dumps(metrics)))
        print('FUTURES_SHADOW_PROMOTION',profile.asset,side,version,json.dumps(metrics,sort_keys=True))
    c.commit()
  return 0
if __name__=='__main__': raise SystemExit(main())
