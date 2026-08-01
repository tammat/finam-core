#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from finam_core.risk.market_shock_gate_v1 import decide_market_shock_gate_v1


MSK = ZoneInfo("Europe/Moscow")


def metrics_at_entry(cur, trade: dict) -> dict:
    entry = trade["entry_ts"]
    start_msk = entry.astimezone(MSK).replace(hour=6, minute=50, second=0, microsecond=0)
    cur.execute("""SELECT ts,high::float8,low::float8,close::float8,
      coalesce(volume,0)::float8 AS volume
      FROM market_bars WHERE symbol=%s AND timeframe='M15' AND ts+interval '15 minutes'<=%s
      ORDER BY ts DESC LIMIT 80""", (trade["symbol"],entry))
    bars=list(reversed(cur.fetchall())); start=start_msk.astimezone(entry.tzinfo)
    prior=[r for r in bars if r["ts"]<start]; current=[r for r in bars if r["ts"]>=start]
    ranges=[max(r["high"]-r["low"],0) for r in prior[-14:]]; atr=sum(ranges)/len(ranges) if ranges else 0
    gap=abs(float(trade["entry_price"])-prior[-1]["close"])/atr if atr and prior else None
    volumes=[r["volume"] for r in prior[-20:] if r["volume"]>0]
    rvol=current[-1]["volume"]/median(volumes) if current and volumes else None
    cur.execute("""SELECT best_bid::float8,best_ask::float8 FROM analytics.market_microstructure_snapshot_v1
      WHERE symbol=%s AND observed_at<=%s AND observed_at>=%s-interval '15 minutes'
        AND best_ask>best_bid ORDER BY observed_at DESC LIMIT 1""",(trade["symbol"],entry,entry))
    quote=cur.fetchone(); spread=(quote["best_ask"]-quote["best_bid"])/atr if quote and atr else None
    return {"bars":len(current),"gap_atr":gap,"spread_atr":spread,"rvol":rvol}


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--days",type=int,default=30)
    parser.add_argument("--output-dir",default="reports"); args=parser.parse_args()
    end=datetime.now(MSK); start=end-timedelta(days=max(1,args.days)); rows=[]
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn,conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id,signal_id,symbol,side,entry_price,entry_ts,net_pnl,portfolio_scope
          FROM closed_trades WHERE trade_source='paper' AND entry_ts>=%s AND entry_ts<%s
            AND portfolio_scope LIKE 'FRESH_V5%%' AND entry_price>0 ORDER BY entry_ts""",(start,end))
        trades=cur.fetchall()
        for trade in trades:
            m=metrics_at_entry(cur,trade)
            decision=decide_market_shock_gate_v1(intent_type='ENTRY',risk_level='RECOVERY',
              completed_m15_bars=m['bars'],gap_atr=m['gap_atr'],spread_atr=m['spread_atr'],
              relative_volume=m['rvol'],market_context_fresh=True,
              recovery_policy_validated=True)
            pnl=float(trade["net_pnl"] or 0); blocked=not decision.allowed
            rows.append({"trade_id":trade["id"],"symbol":trade["symbol"],"side":trade["side"],
              "entry_ts":trade["entry_ts"].isoformat(),"net_pnl_rub":pnl,"blocked":blocked,
              "reason":decision.reason,**m})
        losses=sum(-r['net_pnl_rub'] for r in rows if r['blocked'] and r['net_pnl_rub']<0)
        profits=sum(r['net_pnl_rub'] for r in rows if r['blocked'] and r['net_pnl_rub']>0)
        baseline=sum(r['net_pnl_rub'] for r in rows); gated=sum(r['net_pnl_rub'] for r in rows if not r['blocked'])
        observable=[r for r in rows if r['bars']>=4 and r['gap_atr'] is not None
                    and r['spread_atr'] is not None and r['rvol'] is not None]
        obs_losses=sum(-r['net_pnl_rub'] for r in observable if r['blocked'] and r['net_pnl_rub']<0)
        obs_profits=sum(r['net_pnl_rub'] for r in observable if r['blocked'] and r['net_pnl_rub']>0)
        coverage=len(observable)/len(rows) if rows else 0.0
        policy_verdict=("CANDIDATE_FOR_OOS" if len(observable)>=30 and coverage>=0.80
                        and obs_losses-obs_profits>0 else "KEEP_SHADOW")
        summary={"trades":len(rows),"blocked":sum(r['blocked'] for r in rows),
          "losses_prevented_rub":losses,"profits_foregone_rub":profits,
          "net_protection_rub":losses-profits,"baseline_net_pnl_rub":baseline,
          "gated_net_pnl_rub":gated,"observable_trades":len(observable),
          "observable_coverage":coverage,"observable_losses_prevented_rub":obs_losses,
          "observable_profits_foregone_rub":obs_profits,
          "observable_net_protection_rub":obs_losses-obs_profits,
          "policy_verdict":policy_verdict,"by_reason":dict(defaultdict(int))}
        for r in rows: summary['by_reason'][r['reason']]=summary['by_reason'].get(r['reason'],0)+1
        run_id=str(uuid.uuid4()); cur.execute("""INSERT INTO analytics.market_shock_gate_replay_run_v1
          (run_id,lookback_start,lookback_end,trades_evaluated,trades_blocked,losses_prevented_rub,
           profits_foregone_rub,net_protection_rub,baseline_net_pnl_rub,gated_net_pnl_rub,result_json)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(run_id,start,end,len(rows),summary['blocked'],
          losses,profits,losses-profits,baseline,gated,Json({"summary":summary,"trades":rows})))
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/'market_shock_gate_replay_latest.json').write_text(json.dumps({"summary":summary,"trades":rows},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True));print('paper_changed=0 real_changed=0')
    print('VERDICT=MARKET_SHOCK_GATE_REPLAY_COMPLETE');return 0


if __name__=='__main__': raise SystemExit(main())
