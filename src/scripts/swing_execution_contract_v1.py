from __future__ import annotations
from decimal import Decimal
from scripts.build_strategy_execution_runner_v1 import load_execution_context

def execution_symbol(cursor,symbol):
    root="BR" if symbol.startswith("BR") else ("NG" if symbol.startswith("NG") else None)
    roll=None
    if root:
        cursor.execute("""SELECT selected_symbol,decision_code,days_to_expiry,current_median_volume,next_median_volume
          FROM analytics.futures_roll_decision_v1 WHERE root_symbol=%s ORDER BY created_at DESC LIMIT 1""",(root,))
        roll=cursor.fetchone()
    return (roll["selected_symbol"] if roll and roll["selected_symbol"] else symbol),roll

def load_swing_execution_contract(cursor,symbol):
    selected,roll=execution_symbol(cursor,symbol)
    context=load_execution_context(cursor,selected)
    exchange="RTSX" if selected.endswith("@RTSX") else "MISX"
    asset="FUTURES" if exchange=="RTSX" else "EQUITY"
    cursor.execute("""SELECT bf.broker_fee_code,bf.commission_per_trade,bf.commission_pct,
      bf.source_version broker_source,ef.exchange_fee_code,ef.exchange_fee_per_trade,
      ef.clearing_fee_per_trade,ef.source_version exchange_source,sp.slippage_profile_code,
      sp.slippage_per_trade,sp.source_version slippage_source,tp.tax_profile_code,tp.tax_rate,tp.source_version tax_source
      FROM analytics.broker_fee_profile_v1 bf
      JOIN analytics.exchange_fee_profile_v1 ef USING(exchange_code,asset_class)
      JOIN analytics.slippage_profile_v1 sp USING(exchange_code,asset_class)
      JOIN analytics.account_tax_profile_v1 tp ON tp.account_scope='BASE' AND tp.is_active
      WHERE bf.broker_code='FINAM' AND bf.exchange_code=%s AND bf.asset_class=%s
        AND bf.is_active AND ef.is_active AND sp.is_active AND sp.liquidity_bucket='DEFAULT' LIMIT 1""",(exchange,asset))
    fees=cursor.fetchone()
    result={**context,**(dict(fees) if fees else {}),"research_symbol":symbol,"execution_symbol":selected,
      "exchange_code":exchange,"asset_class":asset,"roll_decision":dict(roll) if roll else None,
      "contract_ready":bool(fees and context.get("contract_spec_source")!="MISSING_SPEC_FALLBACK")}
    if asset=="FUTURES":
      cursor.execute("SELECT * FROM analytics.market_contract_cost_spec_v1 WHERE symbol=%s",(selected,)); official=cursor.fetchone()
      if official:
        result.update({"initial_margin_rub":float(official["initial_margin"]),
          "exchange_fee_per_trade":official["buy_sell_fee"],"scalper_fee":official["scalper_fee"],
          "contract_cost_source":official["source_version"],"contract_cost_verified_at":official["verified_at"]})
      result["contract_ready"]=bool(result["contract_ready"] and official and float(result.get("initial_margin_rub") or 0)>0)
    return result

def notional_rub(price,quantity,contract):
    multiplier=Decimal(str(contract.get("contract_multiplier") or 1)) if contract.get("asset_class")=="FUTURES" else Decimal(str(contract.get("lot_size") or 1))
    return abs(Decimal(str(price))*Decimal(str(quantity))*multiplier)

def cost_bps(price,quantity,contract):
    notional=notional_rub(price,quantity,contract)
    if notional<=0: return Decimal("0")
    fixed=(Decimal(str(contract.get("commission_per_trade") or 0))+Decimal(str(contract.get("exchange_fee_per_trade") or 0))+Decimal(str(contract.get("clearing_fee_per_trade") or 0))+Decimal(str(contract.get("slippage_per_trade") or 0)))*2
    percent=(Decimal(str(contract.get("commission_pct") or 0))*2)*Decimal("10000")
    market=Decimal(str(contract.get("fallback_spread_bps") or 0))+Decimal(str(contract.get("impact_bps_at_max_participation") or 0))*2
    return fixed/notional*Decimal("10000")+percent+market

def gross_pnl_rub(side,entry,exit_price,quantity,contract):
    direction=Decimal("1") if side in ("LONG","BUY") else Decimal("-1")
    move=(Decimal(str(exit_price))-Decimal(str(entry)))*direction
    qty=Decimal(str(quantity))
    if contract.get("asset_class")=="FUTURES":
        tick=Decimal(str(contract.get("tick_size") or 1)); tick_value=Decimal(str(contract.get("tick_value") or 1))
        return move/tick*tick_value*qty
    return move*Decimal(str(contract.get("lot_size") or 1))*qty

def round_trip_cost_rub(entry,quantity,contract):
    return notional_rub(entry,quantity,contract)*cost_bps(entry,quantity,contract)/Decimal("10000")
