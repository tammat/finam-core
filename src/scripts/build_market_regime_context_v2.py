from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

from scripts.build_market_regime_context_v1 import asset_influence, market_state, mx_state, variant_decision


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "MARKET_REGIME_CONTEXT_V2"


def _create_context(cursor) -> dict | None:
    cursor.execute("""WITH buckets AS (
      SELECT date_bin(interval '5 minutes',ts,timestamptz '2001-01-01') ts,
             max(high) high,min(low) low,(array_agg(close ORDER BY ts DESC))[1] close,count(*) n
      FROM market_bars WHERE symbol='MXU6@RTSX' AND timeframe='M1'
        AND ts < date_trunc('minute',clock_timestamp())
      GROUP BY 1)
      SELECT ts,high,low,close FROM buckets
      WHERE n>=3 AND ts+interval '5 minutes'<=clock_timestamp()
      ORDER BY ts DESC LIMIT 61""")
    bars = list(reversed(cursor.fetchall()))
    if len(bars) < 21:
        return None
    mx_bar_ts = bars[-1]["ts"]
    # Use SQL for interval arithmetic; Python receives the exact effective boundary.
    cursor.execute("SELECT %s::timestamptz+interval '5 minutes' effective_ts", (mx_bar_ts,))
    effective_ts = cursor.fetchone()["effective_ts"]
    cursor.execute("""SELECT * FROM analytics.rvi_regime_state_v1
      WHERE bar_ts+interval '1 minute'<=%s
      ORDER BY bar_ts DESC LIMIT 2""", (effective_ts,))
    rvi_rows = cursor.fetchall()
    if not rvi_rows:
        return None
    rvi = rvi_rows[0]
    cursor.execute("""SELECT extract(epoch FROM(clock_timestamp()-%s::timestamptz)) mx_age,
                             extract(epoch FROM(%s::timestamptz-(%s::timestamptz+interval '1 minute'))) rvi_age""",
                   (effective_ts,effective_ts,rvi["bar_ts"]))
    ages = cursor.fetchone()
    if Decimal(str(ages["mx_age"])) > 600:
        print(f"freshness_block mx_age={ages['mx_age']}")
        return None
    rvi_fresh = Decimal(str(ages["rvi_age"])) <= 1800
    mx, strength = mx_state(bars)
    rvi_direction = "FLAT"
    if len(rvi_rows) > 1:
        delta = Decimal(str(rvi_rows[0]["rvi_value"]))-Decimal(str(rvi_rows[1]["rvi_value"]))
        rvi_direction = "RISING" if delta > 0 else "FALLING" if delta < 0 else "FLAT"
    cursor.execute("""INSERT INTO analytics.market_regime_context_v1(
      context_ts,mx_bar_ts,mx_trend,mx_strength,rvi_bar_ts,rvi_value,rvi_percentile,
      rvi_regime,rvi_direction,market_regime,source_version,rvi_fresh)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
      ON CONFLICT(context_ts) DO UPDATE SET mx_bar_ts=excluded.mx_bar_ts,mx_trend=excluded.mx_trend,
      mx_strength=excluded.mx_strength,rvi_bar_ts=excluded.rvi_bar_ts,rvi_value=excluded.rvi_value,
      rvi_percentile=excluded.rvi_percentile,rvi_regime=excluded.rvi_regime,
      rvi_direction=excluded.rvi_direction,market_regime=excluded.market_regime,
      source_version=excluded.source_version,rvi_fresh=excluded.rvi_fresh,
      calculated_at=clock_timestamp() RETURNING *""",
      (effective_ts,mx_bar_ts,mx,strength,rvi["bar_ts"],rvi["rvi_value"],rvi["rolling_percentile"],
       rvi["regime_code"],rvi_direction,
       market_state(mx,rvi["regime_code"] if rvi_fresh else "NORMAL_VOL"),VERSION,rvi_fresh))
    return dict(cursor.fetchone())


def _materialize_variants(cursor) -> int:
    cursor.execute("""SELECT s.*,c.id context_id,c.context_ts,c.mx_trend,c.mx_strength,c.rvi_value,
      c.rvi_regime,c.rvi_direction,c.market_regime,c.rvi_fresh
      FROM signals s JOIN LATERAL (
        SELECT * FROM analytics.market_regime_context_v1 c
        WHERE c.context_ts<=s.ts AND c.source_version='MARKET_REGIME_CONTEXT_V2'
        ORDER BY c.context_ts DESC LIMIT 1) c ON true
      WHERE s.ts>=clock_timestamp()-interval '1 day'
        AND upper(s.status) IN('ACCEPTED','RISK_ACCEPTED','FILLED')
        AND coalesce(s.payload->>'execution_type','')='paper'
        AND coalesce(s.payload->>'portfolio_scope','') LIKE 'FRESH_V5%%'
        AND coalesce(s.payload->>'intent_type','ENTRY')='ENTRY'
        AND NOT EXISTS(SELECT 1 FROM analytics.market_regime_shadow_variant_v1 v
                       WHERE v.parent_signal_id=coalesce(s.signal_id,'signal:'||s.id::text))
      ORDER BY s.ts""")
    written = 0
    for signal in cursor.fetchall():
        context = {key:signal[key] for key in ("mx_trend","mx_strength","rvi_value","rvi_regime","rvi_direction","market_regime","rvi_fresh")}
        for variant in ("BASELINE","MX_FILTERED","MX_RVI_FILTERED"):
            decision,risk,reason = variant_decision(variant,dict(signal),context)
            state = "OPEN" if decision == "INCLUDE" else "SKIPPED"
            cursor.execute("""INSERT INTO analytics.market_regime_shadow_variant_v1(
              parent_signal_id,source_signal_pk,symbol,strategy,side,signal_ts,variant_code,
              decision_code,risk_multiplier,reason_code,context_ts,market_context,source_version,
              entry_price,stop_price,take_price,shadow_state)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
              ON CONFLICT(parent_signal_id,variant_code) DO NOTHING""",
              (signal["signal_id"] or f"signal:{signal['id']}",signal["id"],signal["symbol"],
               signal["strategy"],signal["side"],signal["ts"],variant,decision,risk,reason,
               signal["context_ts"],psycopg2.extras.Json({k:str(v) for k,v in context.items()}),VERSION,
               signal["entry_price"],signal["stop_loss"],signal["take_profit"],state))
            written += cursor.rowcount
    return written


def _close_variants(cursor) -> int:
    cursor.execute("""SELECT v.*,s.qty FROM analytics.market_regime_shadow_variant_v1 v
      JOIN signals s ON s.id=v.source_signal_pk WHERE v.shadow_state='OPEN'
      ORDER BY v.signal_ts LIMIT 500""")
    closed = 0
    for row in cursor.fetchall():
        cursor.execute("""SELECT ts,close FROM market_bars WHERE symbol=%s AND timeframe='M1'
          AND ts>%s AND ts<date_trunc('minute',clock_timestamp()) ORDER BY ts""",
          (row["symbol"],row["signal_ts"]))
        bars = cursor.fetchall()
        if not bars:
            continue
        side = str(row["side"]).upper(); direction = Decimal("1") if side in {"BUY","LONG"} else Decimal("-1")
        exit_bar = None; exit_reason = None
        for bar in bars:
            close = Decimal(str(bar["close"])); held=(bar["ts"]-row["signal_ts"]).total_seconds()
            stop = Decimal(str(row["stop_price"])) if row["stop_price"] is not None else None
            take = Decimal(str(row["take_price"])) if row["take_price"] is not None else None
            if stop is not None and direction*(close-stop) <= 0:
                exit_bar,exit_reason=bar,"STOP_CLOSE_CONFIRMED"; break
            if take is not None and direction*(close-take) >= 0:
                exit_bar,exit_reason=bar,"TARGET_CLOSE_CONFIRMED"; break
            if held >= 3600:
                exit_bar,exit_reason=bar,"SHADOW_MAX_HOLD_60M"; break
        if exit_bar is None:
            continue
        cursor.execute("""SELECT CASE WHEN upper(%s) LIKE '%%@RTSX' THEN tick_value/nullif(tick_size,0)
          ELSE lot_size END multiplier,
          CASE WHEN upper(%s) LIKE '%%@RTSX' THEN tick_value ELSE tick_size*lot_size END tick_cost
          FROM analytics.market_contract_spec_v1 WHERE is_active AND symbol=%s
          ORDER BY valid_from DESC LIMIT 1""", (row["symbol"],row["symbol"],row["symbol"]))
        spec = cursor.fetchone()
        if not spec or not spec["multiplier"] or not spec["tick_cost"]:
            continue
        qty=Decimal(str(row["qty"] or 1))*Decimal(str(row["risk_multiplier"])); entry=Decimal(str(row["entry_price"])); exit_price=Decimal(str(exit_bar["close"]))
        gross=(exit_price-entry)*direction*qty*Decimal(str(spec["multiplier"])); cost=Decimal("2")*qty*Decimal(str(spec["tick_cost"])); net=gross-cost
        cursor.execute("""UPDATE analytics.market_regime_shadow_variant_v1 SET shadow_state='CLOSED',
          exit_ts=%s,exit_price=%s,exit_reason=%s,gross_pnl=%s,execution_cost=%s,net_pnl=%s,
          closed_at=clock_timestamp() WHERE id=%s""",
          (exit_bar["ts"],exit_price,exit_reason,gross,cost,net,row["id"]))
        closed += cursor.rowcount
    return closed


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            context=_create_context(cursor)
            if context is None:
                print("VERDICT=MARKET_REGIME_CONTEXT_V2_FRESHNESS_BLOCK")
                return 0
            written=_materialize_variants(cursor); closed=_close_variants(cursor)
    print(f"context_ts={context['context_ts']} mx={context['mx_trend']} rvi={context['rvi_regime']} market={context['market_regime']} variants={written} closed={closed}")
    print("paper_changed=0 real_changed=0")
    print("VERDICT=MARKET_REGIME_CONTEXT_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
