from __future__ import annotations
import hashlib,json,math,os,uuid
from decimal import Decimal
import psycopg2,psycopg2.extras
from marketcore.research.dynamic_exit_v1 import dynamic_exit_v1
from scripts.run_swing_forward_shadow_router_v1 import side_for
from scripts.swing_execution_contract_v1 import gross_pnl_rub,load_swing_execution_contract,notional_rub,round_trip_cost_rub

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
NS=uuid.UUID("bd41510d-34c8-55e4-9bdf-6c0fde3ae8c0")
SOURCE="SWING_CANONICAL_PAPER_ENGINE_V1"
def safe(v): return json.loads(json.dumps(v,default=str))
def candidate_key(process_id): return uuid.UUID(str(process_id)).int%(2**62)

def swing_exit_decision(bars,entry_ts,side,params):
  """Evaluate an open swing position using closed bars available so far."""
  entry_index=next((index for index,bar in enumerate(bars) if bar["ts"]==entry_ts),None)
  if entry_index is None or entry_index>=len(bars)-1: return None
  hold=int(params.get("holding_bars",6))
  dynamic_hold=int(params.get("exit_max_holding_bars",max(hold,20)))
  maximum_hold=dynamic_hold if str(params.get("exit_policy_code","FIXED_HOLD"))=="DYNAMIC_EXIT_V1" else hold
  decision=dynamic_exit_v1([float(bar["close"]) for bar in bars],entry_index,1 if side=="LONG" else -1,maximum_hold,params)
  held=decision.exit_index-entry_index
  # dynamic_exit_v1 returns the last available index when the horizon has not
  # elapsed; that is an observation, not an exit in an incremental Paper run.
  if decision.reason_code in ("MAX_HOLD","FIXED_HOLD") and held<maximum_hold: return None
  return bars[decision.exit_index],decision.reason_code

def fill_costs(price,qty,contract):
  notional=notional_rub(price,qty,contract)
  commission=Decimal(str(contract.get("commission_per_trade") or 0))+notional*Decimal(str(contract.get("commission_pct") or 0))
  exchange=Decimal(str(contract.get("exchange_fee_per_trade") or 0)); clearing=Decimal(str(contract.get("clearing_fee_per_trade") or 0))
  market_bps=Decimal(str(contract.get("fallback_spread_bps") or 0))/2+Decimal(str(contract.get("impact_bps_at_max_participation") or 0))
  slippage=Decimal(str(contract.get("slippage_per_trade") or 0))+notional*market_bps/Decimal("10000")
  return commission,exchange,clearing,slippage

def create_order_fill(q,process,ts,side,qty,price,reason,contract):
  key=f"{process}:{ts.isoformat()}:{side}:{reason}"; order_id=uuid.uuid5(NS,key); fill_id=uuid.uuid5(NS,key+":FILL")
  q.execute("""INSERT INTO analytics.swing_paper_order_v1(order_id,process_id,signal_ts,side,quantity,reference_price,order_type,order_status,reason_code,execution_contract)
    VALUES(%s,%s,%s,%s,%s,%s,'MARKET_MODEL','FILLED',%s,%s) ON CONFLICT DO NOTHING""",
    (order_id,process,ts,side,qty,price,reason,psycopg2.extras.Json(safe(contract))))
  commission,exchange,clearing,slippage=fill_costs(price,qty,contract)
  q.execute("""INSERT INTO analytics.swing_paper_fill_v1(fill_id,order_id,fill_ts,fill_price,quantity,commission,exchange_fee,clearing_fee,slippage,source_version)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
    (fill_id,order_id,ts,price,qty,commission,exchange,clearing,slippage,SOURCE))
  return order_id,commission+exchange+clearing+slippage

def cluster_for(symbol):
  base=symbol.split("@",1)[0]
  return "OIL" if base.startswith("BR") else "GAS" if base.startswith("NG") else base

def risk_state(q,process,symbol,strategy_family,policy):
  q.execute("SELECT EXISTS(SELECT 1 FROM public.persistent_kill_switch WHERE active AND (scope='GLOBAL' OR symbol=%s)) active",(symbol,)); killed=bool(q.fetchone()["active"])
  q.execute("SELECT count(*) open,coalesce(sum(exposure_rub),0) exposure,coalesce(sum(margin_used_rub),0) margin FROM analytics.swing_paper_position_v1 WHERE status_code='OPEN'"); portfolio=q.fetchone()
  q.execute("SELECT coalesce(sum(net_pnl),0) pnl FROM analytics.swing_paper_trade_v1 WHERE exit_ts::date=current_date"); daily=Decimal(str(q.fetchone()["pnl"] or 0))
  q.execute("""WITH x AS(SELECT created_at,sum(net_pnl) OVER(ORDER BY created_at) cumulative FROM analytics.swing_paper_trade_v1),s AS(SELECT coalesce(max(cumulative),0) peak,coalesce((SELECT cumulative FROM x ORDER BY created_at DESC LIMIT 1),0) current FROM x) SELECT peak-current drawdown FROM s"""); drawdown=Decimal(str(q.fetchone()["drawdown"] or 0))
  equity=Decimal(str(policy["paper_equity_rub"])); reasons=[]
  if killed: reasons.append("KILL_SWITCH_ACTIVE")
  if int(portfolio["open"])>=int(policy["max_open_positions"]): reasons.append("MAX_OPEN_POSITIONS")
  if Decimal(str(portfolio["exposure"]))>=equity*Decimal(str(policy["max_gross_leverage"])): reasons.append("GROSS_LEVERAGE_LIMIT")
  if Decimal(str(portfolio["margin"]))>=equity*Decimal(str(policy["max_margin_share"])): reasons.append("MARGIN_LIMIT")
  if daily<=-equity*Decimal(str(policy["max_daily_loss_share"])): reasons.append("DAILY_LOSS_LIMIT")
  if drawdown>=equity*Decimal(str(policy["max_drawdown_share"])): reasons.append("DRAWDOWN_LIMIT")
  q.execute("""SELECT s.symbol FROM analytics.swing_paper_position_v1 p
    JOIN analytics.swing_paper_strategy_v1 s USING(process_id)
    WHERE p.status_code='OPEN' AND p.process_id<>%s""",(process,))
  if sum(cluster_for(row["symbol"])==cluster_for(symbol) for row in q.fetchall()) >= int(policy.get("max_positions_per_cluster",1)): reasons.append("CLUSTER_EXPOSURE_LIMIT")
  q.execute("""SELECT count(*) n,coalesce(avg(t.net_pnl),0) expectancy
    FROM analytics.swing_paper_trade_v1 t JOIN analytics.swing_paper_strategy_v1 s USING(process_id)
    WHERE s.strategy_family=%s""",(strategy_family,)); history=q.fetchone()
  if int(history["n"])>=int(policy.get("degradation_min_closed_trades",10)) and Decimal(str(history["expectancy"]))<=0: reasons.append("STRATEGY_DEGRADATION")
  q.execute("""SELECT observed_at,best_bid,best_ask,spread_bps,bid_depth,ask_depth
    FROM analytics.market_microstructure_snapshot_v1 WHERE symbol=%s
    ORDER BY observed_at DESC LIMIT 1""",(symbol,)); quote=q.fetchone()
  if not quote: reasons.append("MICROSTRUCTURE_MISSING")
  else:
    age=__import__('time').time()-quote["observed_at"].timestamp()
    if age>float(policy.get("max_quote_age_seconds",30)): reasons.append("QUOTE_STALE")
    if quote["best_bid"] is None or quote["best_ask"] is None or Decimal(str(quote["best_bid"]))>=Decimal(str(quote["best_ask"])): reasons.append("BOOK_INVALID")
    if Decimal(str(quote["spread_bps"] or 0))>Decimal(str(policy.get("max_spread_bps",25))): reasons.append("SPREAD_TOO_WIDE")
    if min(Decimal(str(quote["bid_depth"] or 0)),Decimal(str(quote["ask_depth"] or 0)))<Decimal(str(policy.get("min_book_depth",1))): reasons.append("BOOK_DEPTH_INSUFFICIENT")
  return not reasons,reasons,dict(portfolio),daily,drawdown,quote

def quantity_for(price,contract,policy,portfolio):
  equity=Decimal(str(policy["paper_equity_rub"])); target=equity*Decimal(str(policy["max_position_share"]))
  unit=notional_rub(price,1,contract); qty=math.floor(float(target/unit)) if unit>0 else 0
  # Сначала допустимый убыток до стопа, затем пределы экспозиции/маржи.
  risk_per_contract=unit*Decimal(str(policy.get("default_stop_loss_bps",80)))/Decimal("10000")+sum(fill_costs(price,Decimal("1"),contract))*Decimal("2")
  risk_budget=equity*Decimal(str(policy.get("max_risk_per_trade_share",0.01)))
  by_risk=math.floor(float(risk_budget/risk_per_contract)) if risk_per_contract>0 else 0
  qty=min(qty,by_risk)
  if contract.get("asset_class")=="FUTURES":
    margin=Decimal(str(contract.get("initial_margin_rub") or 0))
    if margin<=0: return Decimal("0"),risk_budget,risk_per_contract
    margin_budget=max(Decimal("0"),equity*Decimal(str(policy["max_margin_share"]))-Decimal(str(portfolio["margin"])))
    exposure_budget=max(Decimal("0"),equity*Decimal(str(policy["max_gross_leverage"]))-Decimal(str(portfolio["exposure"])))
    by_margin=math.floor(float(margin_budget/margin))
    by_leverage=math.floor(float(exposure_budget/unit)) if unit>0 else 0
    qty=min(by_margin,by_leverage,int(policy["max_contracts_per_position"]))
  step=Decimal(str(contract.get("quantity_step") or 1)); return (Decimal(str(max(0,qty)))//step)*step,risk_budget,risk_per_contract

def main():
  opened=closed=blocked=mtm=0
  with psycopg2.connect(DB) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
      q.execute("SELECT pg_try_advisory_lock(741903148) locked")
      if not q.fetchone()["locked"]: print("VERDICT=SWING_PAPER_ENGINE_ALREADY_RUNNING"); return 0
      q.execute("SELECT policy FROM analytics.swing_paper_risk_policy_v1 WHERE active LIMIT 1"); policy=q.fetchone()["policy"]
      q.execute("""SELECT l.process_id,a.admitted_at,i.strategy_family,i.symbol,i.timeframe,i.parameter_snapshot,i.hypothesis_id
        FROM analytics.swing_candidate_lifecycle_v1 l JOIN analytics.swing_paper_admission_v1 a USING(process_id)
        JOIN analytics.swing_next_research_plan_item_v1 i ON i.plan_item_id=l.plan_item_id
        WHERE l.stage_code='PAPER' AND l.status_code='READY' AND l.paper_allowed AND a.paper_allowed AND NOT l.live_allowed""")
      candidates=q.fetchall()
      for c in candidates:
        process=c["process_id"]; key=candidate_key(process)
        q.execute("""INSERT INTO analytics.swing_paper_strategy_v1(process_id,candidate_key,strategy_family,symbol,timeframe,parameter_snapshot,status_code)
          VALUES(%s,%s,%s,%s,%s,%s,'ACTIVE') ON CONFLICT DO NOTHING""",(process,key,c["strategy_family"],c["symbol"],c["timeframe"],psycopg2.extras.Json(c["parameter_snapshot"])))
        q.execute("INSERT INTO analytics.swing_paper_position_v1(process_id,status_code) VALUES(%s,'FLAT') ON CONFLICT DO NOTHING",(process,))
        allowed,reasons,portfolio,daily,drawdown,quote=risk_state(q,process,c["symbol"],c["strategy_family"],policy)
        decision="ALLOW" if allowed else "BLOCK"
        q.execute("INSERT INTO analytics.swing_paper_risk_decision_v1(process_id,decision_code,reason_codes,open_positions,gross_exposure_rub,daily_pnl,drawdown,policy_snapshot) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
          (process,decision,psycopg2.extras.Json(reasons),portfolio["open"],portfolio["exposure"],daily,drawdown,psycopg2.extras.Json(policy)))
        q.execute("""INSERT INTO analytics.risk_control_decision_v2(
          decision_id,process_id,symbol,strategy_family,decision_code,reason_codes,
          gross_exposure_rub,daily_pnl_rub,drawdown_rub,spread_bps,book_depth,quote_observed_at,policy_snapshot)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (uuid.uuid4(),process,c["symbol"],c["strategy_family"],decision,psycopg2.extras.Json(reasons),
           portfolio["exposure"],daily,drawdown,
           quote["spread_bps"] if quote else None,
           min(Decimal(str(quote["bid_depth"] or 0)),Decimal(str(quote["ask_depth"] or 0))) if quote else None,
           quote["observed_at"] if quote else None,psycopg2.extras.Json(policy)))
        if not allowed:
          q.execute("UPDATE analytics.swing_paper_strategy_v1 SET status_code='BLOCKED',updated_at=clock_timestamp() WHERE process_id=%s",(process,)); blocked+=1
          q.execute("SELECT status_code FROM analytics.swing_paper_position_v1 WHERE process_id=%s",(process,)); existing=q.fetchone()
          if not existing or existing["status_code"]!='OPEN': continue
        else:
          q.execute("UPDATE analytics.swing_paper_strategy_v1 SET status_code='ACTIVE',updated_at=clock_timestamp() WHERE process_id=%s",(process,))
        contract=load_swing_execution_contract(q,c["symbol"])
        if not contract.get("contract_ready"):
          q.execute("UPDATE analytics.swing_paper_strategy_v1 SET status_code='BLOCKED',updated_at=clock_timestamp() WHERE process_id=%s",(process,)); blocked+=1; continue
        q.execute("SELECT * FROM analytics.swing_paper_position_v1 WHERE process_id=%s FOR UPDATE",(process,)); position=q.fetchone()
        q.execute("SELECT last_evaluated_ts FROM analytics.swing_paper_worker_state_v1 WHERE process_id=%s",(process,)); state=q.fetchone(); last=state["last_evaluated_ts"] if state and state["last_evaluated_ts"] else c["admitted_at"]
        q.execute("SELECT ts,open,high,low,close FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s ORDER BY ts",(c["symbol"],c["timeframe"])); bars=q.fetchall(); new=[b for b in bars if b["ts"]>last]
        if position["status_code"]=="OPEN":
          exit_decision=swing_exit_decision(bars,position["entry_ts"],position["side"],c["parameter_snapshot"])
          if exit_decision:
            bar,exit_reason=exit_decision; exit_price=Decimal(str(bar["close"])); exit_side="SELL" if position["side"]=="LONG" else "BUY"
            exit_order,exit_cost=create_order_fill(q,process,bar["ts"],exit_side,position["quantity"],exit_price,exit_reason,contract)
            q.execute("SELECT order_id FROM analytics.swing_paper_order_v1 WHERE process_id=%s AND signal_ts=%s AND reason_code='SIGNAL_ENTRY'",(process,position["entry_ts"])); entry_order=q.fetchone()["order_id"]
            gross=gross_pnl_rub(position["side"],position["entry_price"],exit_price,position["quantity"],contract); total=Decimal(str(position["entry_cost"]))+exit_cost; net=gross-total; tax=max(Decimal("0"),net*Decimal(str(contract.get("tax_rate") or 0)))
            trade_id=uuid.uuid5(NS,f"{process}:{position['entry_ts'].isoformat()}:TRADE")
            q.execute("""INSERT INTO analytics.swing_paper_trade_v1(trade_id,process_id,entry_order_id,exit_order_id,side,quantity,entry_ts,exit_ts,entry_price,exit_price,gross_pnl,total_cost,net_pnl,estimated_tax,net_after_tax,exit_reason)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
              (trade_id,process,entry_order,exit_order,position["side"],position["quantity"],position["entry_ts"],bar["ts"],position["entry_price"],exit_price,gross,total,net,tax,net-tax,exit_reason))
            q.execute("UPDATE analytics.swing_paper_position_v1 SET side=NULL,quantity=0,entry_ts=NULL,entry_price=NULL,last_price=%s,bars_held=0,status_code='FLAT',entry_cost=0,exposure_rub=0,margin_used_rub=0,unrealized_pnl=0,updated_at=clock_timestamp() WHERE process_id=%s",(exit_price,process)); closed+=1; position={"status_code":"FLAT"}
        if position["status_code"]=="FLAT" and new and allowed:
          bar=new[-1]; target=[b for b in bars if b["ts"]<=bar["ts"]]; params=c["parameter_snapshot"]; benchmark=None; benchmark_symbol=params.get("benchmark") or params.get("source")
          if benchmark_symbol:
            q.execute("SELECT ts,open,high,low,close FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s AND ts<=%s ORDER BY ts",(benchmark_symbol,c["timeframe"],bar["ts"])); benchmark=q.fetchall()
          candidate={"frozen_parameter_json":params,"strategy_family":c["strategy_family"]}; side=side_for(candidate,target,benchmark)
          if side:
            price=Decimal(str(bar["close"])); qty,risk_budget,risk_per_contract=quantity_for(price,contract,policy,portfolio)
            q.execute("""UPDATE analytics.risk_control_decision_v2 SET requested_quantity=%s,
              approved_quantity=%s,risk_budget_rub=%s,risk_per_contract_rub=%s
              WHERE decision_id=(SELECT decision_id FROM analytics.risk_control_decision_v2
                WHERE process_id=%s ORDER BY created_at DESC LIMIT 1)""",
              (qty,qty,risk_budget,risk_per_contract,process))
            if qty>0:
              order_side="BUY" if side=="LONG" else "SELL"; order,entry_cost=create_order_fill(q,process,bar["ts"],order_side,qty,price,"SIGNAL_ENTRY",contract)
              exposure=notional_rub(price,qty,contract); margin=Decimal(str(contract.get("initial_margin_rub") or 0))*qty if contract.get("asset_class")=="FUTURES" else Decimal("0")
              q.execute("UPDATE analytics.swing_paper_position_v1 SET side=%s,quantity=%s,entry_ts=%s,entry_price=%s,last_price=%s,status_code='OPEN',entry_cost=%s,exposure_rub=%s,margin_used_rub=%s,updated_at=clock_timestamp() WHERE process_id=%s",(side,qty,bar["ts"],price,price,entry_cost,exposure,margin,process)); opened+=1
        latest=bars[-1] if bars else None
        if latest:
          q.execute("SELECT * FROM analytics.swing_paper_position_v1 WHERE process_id=%s",(process,)); pos=q.fetchone(); unrealized=Decimal("0")
          if pos["status_code"]=="OPEN": unrealized=gross_pnl_rub(pos["side"],pos["entry_price"],latest["close"],pos["quantity"],contract)-Decimal(str(pos["entry_cost"])); q.execute("UPDATE analytics.swing_paper_position_v1 SET last_price=%s,unrealized_pnl=%s,updated_at=clock_timestamp() WHERE process_id=%s",(latest["close"],unrealized,process))
          q.execute("SELECT count(*) trades,coalesce(sum(gross_pnl),0) gross,coalesce(sum(total_cost),0) costs,coalesce(sum(net_pnl),0) net,coalesce(sum(estimated_tax),0) tax FROM analytics.swing_paper_trade_v1 WHERE process_id=%s",(process,)); totals=q.fetchone()
          q.execute("""WITH x AS(SELECT created_at,sum(net_pnl) OVER(ORDER BY created_at) cumulative FROM analytics.swing_paper_trade_v1 WHERE process_id=%s),y AS(SELECT cumulative,max(cumulative) OVER(ORDER BY created_at) peak FROM x) SELECT coalesce(max(peak-cumulative),0) drawdown FROM y""",(process,)); process_drawdown=q.fetchone()["drawdown"]
          q.execute("""INSERT INTO analytics.paper_portfolio_mtm_v1(candidate_id,strategy_code,symbol,timeframe,trades,gross_pnl,commission,slippage,net_pnl,max_drawdown,paper_status,source_version,estimated_tax,net_after_tax)
            VALUES(%s,%s,%s,%s,%s,%s,%s,0,%s,%s,'ACTIVE',%s,%s,%s)""",(key,c["strategy_family"],c["symbol"],c["timeframe"],totals["trades"],totals["gross"],totals["costs"],Decimal(str(totals["net"]))+unrealized,process_drawdown,SOURCE,totals["tax"],Decimal(str(totals["net"]))-Decimal(str(totals["tax"]))+unrealized)); mtm+=1
          q.execute("""INSERT INTO analytics.swing_paper_worker_state_v1(process_id,last_evaluated_ts,worker_status,last_error) VALUES(%s,%s,'OK',NULL)
            ON CONFLICT(process_id) DO UPDATE SET last_evaluated_ts=excluded.last_evaluated_ts,worker_status='OK',last_error=NULL,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp()""",(process,latest["ts"]))
  print(f"strategies={len(candidates)}");print(f"opened={opened}");print(f"closed={closed}");print(f"blocked={blocked}");print(f"mtm={mtm}");print("broker_orders=0");print("live_allowed=0");print("VERDICT=SWING_PAPER_ENGINE_V1_OK");return 0
if __name__=="__main__": raise SystemExit(main())
