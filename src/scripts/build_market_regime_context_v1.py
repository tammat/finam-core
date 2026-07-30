from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "MARKET_REGIME_CONTEXT_V1"


def mx_state(bars: list[dict]) -> tuple[str, Decimal]:
    if len(bars) < 21:
        return "UNKNOWN", Decimal("0")
    first, last = Decimal(str(bars[-21]["close"])), Decimal(str(bars[-1]["close"]))
    ranges = [Decimal(str(row["high"]))-Decimal(str(row["low"])) for row in bars[-20:]]
    atr = sum(ranges, Decimal("0"))/Decimal(len(ranges))
    normalized = (last-first)/atr if atr > 0 else Decimal("0")
    direction = "UP" if normalized >= Decimal("0.5") else "DOWN" if normalized <= Decimal("-0.5") else "RANGE"
    return direction, min(Decimal("1"), abs(normalized)/Decimal("3"))


def market_state(mx: str, rvi: str) -> str:
    if rvi == "HIGH_VOL":
        return "STRESS" if mx == "DOWN" else "HIGH_VOLATILITY"
    if mx == "UP":
        return "RISK_ON"
    if mx == "DOWN":
        return "RISK_OFF"
    return "RANGE"


def asset_influence(symbol: str) -> str:
    value = symbol.upper()
    if value.startswith("MX") or value.endswith("@MISX"):
        return "STRONG"
    if value.startswith(("USD", "CNY", "SI")):
        return "MODERATE"
    return "WEAK"


def variant_decision(variant: str, signal: dict, context: dict) -> tuple[str, Decimal, str]:
    if variant == "BASELINE":
        return "INCLUDE", Decimal("1"), "CURRENT_RULES"
    side = str(signal.get("side") or "").upper()
    strategy = str(signal.get("strategy") or "").upper()
    mx = context["mx_trend"]
    aligned = (side in {"BUY","LONG"} and mx == "UP") or (side in {"SELL","SHORT"} and mx == "DOWN")
    influence = asset_influence(str(signal.get("symbol") or ""))
    if influence == "WEAK":
        return "INCLUDE", Decimal("1"), "MARKET_CONTEXT_ADVISORY_WEAK_INFLUENCE"
    if not aligned:
        return "SKIP", Decimal("0"), "MX_DIRECTION_NOT_CONFIRMED"
    if variant == "MX_FILTERED":
        return "INCLUDE", Decimal("0.85" if influence == "STRONG" else "1"), "MX_DIRECTION_CONFIRMED"
    if not context.get("rvi_fresh", True):
        return "SKIP", Decimal("0"), "RVI_STALE"
    mean_reversion = any(code in strategy for code in ("MEAN_REVERSION","VWAP_BANDS","_MR","RANGE_"))
    rvi = context["rvi_regime"]
    allowed = rvi in ({"LOW_VOL","NORMAL_VOL"} if mean_reversion else {"NORMAL_VOL","HIGH_VOL"})
    if not allowed:
        return "SKIP", Decimal("0"), "RVI_REGIME_NOT_COMPATIBLE"
    risk = Decimal("0.50") if rvi == "HIGH_VOL" else Decimal("0.75") if rvi == "NORMAL_VOL" else Decimal("1")
    return "INCLUDE", risk, "MX_AND_RVI_CONFIRMED"


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT ts,high,low,close FROM market_bars WHERE symbol='MXU6@RTSX'
                AND timeframe='M5' AND ts < date_trunc('minute',clock_timestamp())-interval '5 minutes'
                ORDER BY ts DESC LIMIT 61""")
            bars = list(reversed(cursor.fetchall()))
            if len(bars) < 21:
                print("VERDICT=MARKET_REGIME_WAITING_MX_BARS")
                return 0
            mx, strength = mx_state(bars)
            cursor.execute("""SELECT * FROM analytics.rvi_regime_state_v1 ORDER BY bar_ts DESC LIMIT 2""")
            rvi_rows = cursor.fetchall()
            if not rvi_rows:
                print("VERDICT=MARKET_REGIME_WAITING_RVI")
                return 0
            rvi = rvi_rows[0]
            rvi_direction = "FLAT"
            if len(rvi_rows) > 1:
                delta = Decimal(str(rvi_rows[0]["rvi_value"]))-Decimal(str(rvi_rows[1]["rvi_value"]))
                rvi_direction = "RISING" if delta > 0 else "FALLING" if delta < 0 else "FLAT"
            context_ts = min(bars[-1]["ts"],rvi["bar_ts"])
            cursor.execute("""INSERT INTO analytics.market_regime_context_v1(
                context_ts,mx_bar_ts,mx_trend,mx_strength,rvi_bar_ts,rvi_value,rvi_percentile,
                rvi_regime,rvi_direction,market_regime,source_version)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
              ON CONFLICT(context_ts) DO UPDATE SET mx_trend=excluded.mx_trend,mx_strength=excluded.mx_strength,
                rvi_value=excluded.rvi_value,rvi_percentile=excluded.rvi_percentile,
                rvi_regime=excluded.rvi_regime,rvi_direction=excluded.rvi_direction,
                market_regime=excluded.market_regime,calculated_at=clock_timestamp()
              RETURNING *""", (context_ts,bars[-1]["ts"],mx,strength,rvi["bar_ts"],rvi["rvi_value"],
                rvi["rolling_percentile"],rvi["regime_code"],rvi_direction,
                market_state(mx,rvi["regime_code"]),VERSION))
            context = dict(cursor.fetchone())
            cursor.execute("""SELECT s.* FROM signals s
                WHERE s.ts >= %s-interval '10 minutes' AND s.ts <= %s
                  AND coalesce(s.payload->>'intent_type','ENTRY')='ENTRY'""", (context_ts,context_ts))
            signals = cursor.fetchall()
            written = 0
            for signal in signals:
                for variant in ("BASELINE","MX_FILTERED","MX_RVI_FILTERED"):
                    decision,risk,reason = variant_decision(variant,dict(signal),context)
                    cursor.execute("""INSERT INTO analytics.market_regime_shadow_variant_v1(
                        parent_signal_id,source_signal_pk,symbol,strategy,side,signal_ts,variant_code,
                        decision_code,risk_multiplier,reason_code,context_ts,market_context,source_version)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(parent_signal_id,variant_code) DO NOTHING""",
                      (signal["signal_id"] or f"signal:{signal['id']}",signal["id"],signal["symbol"],
                       signal["strategy"],signal["side"],signal["ts"],variant,decision,risk,reason,
                       context_ts,psycopg2.extras.Json({k:str(context[k]) for k in
                         ("mx_trend","mx_strength","rvi_value","rvi_regime","rvi_direction","market_regime")}),VERSION))
                    written += cursor.rowcount
    print(f"context_ts={context_ts} mx={mx} strength={strength} rvi={rvi['regime_code']} market={context['market_regime']} variants={written}")
    print("paper_changed=0 real_changed=0")
    print("VERDICT=MARKET_REGIME_CONTEXT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
