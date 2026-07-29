#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from statistics import median

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.futures_risk_calibrator import (
    CalibrationBounds,
    TradePathObservation,
    calibrate_profile,
)
from finam_core.strategy.futures_adaptive_risk_policy import FuturesAdaptiveRiskPolicy


TIMEFRAMES = {"NG": "M1", "BR": "M5", "USD": "M5", "CNY": "M5", "GOLD": "M5"}


def connection():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def asset_for(symbol: str) -> str | None:
    profile = FuturesAdaptiveRiskPolicy().profile_for(symbol)
    return profile.asset if profile else None


def atr_at_entry(cursor, symbol: str, timeframe: str, entry_ts: datetime) -> float | None:
    cursor.execute(
        """
        SELECT high::float8,low::float8,close::float8
        FROM market_bars
        WHERE symbol=%s AND timeframe=%s AND ts<=%s
        ORDER BY ts DESC LIMIT 15
        """,
        (symbol, timeframe, entry_ts),
    )
    rows = list(reversed(cursor.fetchall()))
    if len(rows) < 15:
        return None
    ranges = []
    for previous, current in zip(rows, rows[1:]):
        ranges.append(max(
            current["high"] - current["low"],
            abs(current["high"] - previous["close"]),
            abs(current["low"] - previous["close"]),
        ))
    return sum(ranges) / len(ranges) if ranges else None


def path_observation(cursor, trade: dict, timeframe: str) -> TradePathObservation | None:
    atr = atr_at_entry(cursor, trade["symbol"], timeframe, trade["entry_ts"])
    if not atr or atr <= 0:
        return None
    cursor.execute(
        """
        SELECT max(high)::float8 AS max_high,min(low)::float8 AS min_low
        FROM market_bars
        WHERE symbol=%s AND timeframe=%s AND ts BETWEEN %s AND %s
        """,
        (trade["symbol"], timeframe, trade["entry_ts"], trade["exit_ts"]),
    )
    path = cursor.fetchone()
    if not path or path["max_high"] is None or path["min_low"] is None:
        return None
    entry = float(trade["entry_price"])
    side = str(trade["side"]).upper()
    if side in {"LONG", "BUY"}:
        mae = max(0.0, entry - float(path["min_low"]))
        mfe = max(0.0, float(path["max_high"]) - entry)
    else:
        mae = max(0.0, float(path["max_high"]) - entry)
        mfe = max(0.0, entry - float(path["min_low"]))

    cursor.execute(
        """
        WITH current_bar AS (
          SELECT volume::float8 AS volume FROM market_bars
          WHERE symbol=%s AND timeframe=%s AND ts<=%s ORDER BY ts DESC LIMIT 1
        ), history AS (
          SELECT volume::float8 AS volume FROM market_bars
          WHERE symbol=%s AND timeframe=%s AND ts<%s AND volume>0 ORDER BY ts DESC LIMIT 20
        )
        SELECT (SELECT volume FROM current_bar) AS current_volume,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY volume) AS median_volume
        FROM history
        """,
        (trade["symbol"], timeframe, trade["entry_ts"], trade["symbol"], timeframe, trade["entry_ts"]),
    )
    volume_row = cursor.fetchone() or {}
    baseline = float(volume_row.get("median_volume") or 0.0)
    current_volume = float(volume_row.get("current_volume") or 0.0)
    volume_ratio = current_volume / baseline if baseline > 0 else None
    return TradePathObservation(
        profitable=float(trade["net_pnl"] or 0.0) > 0,
        mae_atr=mae / atr,
        mfe_atr=mfe / atr,
        volume_ratio=volume_ratio,
    )


def main() -> int:
    policy = FuturesAdaptiveRiskPolicy()
    grouped: dict[tuple[str, str], list[TradePathObservation]] = defaultdict(list)
    with connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT symbol,upper(side) AS side,entry_price,net_pnl,
                   coalesce(entry_ts,opened_at,created_at) AS entry_ts,
                   coalesce(closed_at,exit_ts,created_at) AS exit_ts
            FROM closed_trades
            WHERE symbol LIKE '%%@RTSX'
              AND trade_source='paper'
              AND coalesce(payload->'context'->>'cohort','') LIKE 'FRESH_V5%%'
              AND coalesce(entry_ts,opened_at,created_at) IS NOT NULL
              AND coalesce(closed_at,exit_ts,created_at) IS NOT NULL
              AND coalesce(closed_at,exit_ts,created_at) >= current_date - interval '180 days'
            ORDER BY coalesce(closed_at,exit_ts,created_at) DESC
            LIMIT 1000
            """
        )
        for trade in cursor.fetchall():
            asset = asset_for(trade["symbol"])
            if not asset:
                continue
            side = "LONG" if trade["side"] in {"LONG", "BUY"} else "SHORT"
            observation = path_observation(cursor, trade, TIMEFRAMES[asset])
            if observation:
                grouped[(asset, side)].append(observation)

        for profile in policy.PROFILES:
            for side in ("LONG", "SHORT"):
                observations = grouped.get((profile.asset, side), [])
                result = calibrate_profile(
                    observations,
                    CalibrationBounds(
                        profile.min_stop_atr,
                        profile.max_stop_atr,
                        profile.target_atr,
                        profile.min_reward_r,
                        profile.min_volume_ratio,
                    ),
                )
                payload = {
                    "version": "v1",
                    "lookback_days": 180,
                    "cohort_filter": "FRESH_V5%",
                    "trade_source": "paper",
                    "method": "MAE_Q80_PLUS_0_10_MFE_Q70",
                }
                cursor.execute(
                    """
                    INSERT INTO analytics.futures_risk_calibration_v1 (
                      calibration_date,asset_code,side_code,timeframe_code,trades,winners,
                      mae_q80_atr,mfe_q70_atr,current_stop_atr,current_take_atr,current_volume_ratio,
                      recommended_stop_atr,recommended_take_atr,recommended_volume_ratio,
                      recommendation_status,reason_code,payload,generated_at
                    ) VALUES (current_date,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,clock_timestamp())
                    ON CONFLICT (calibration_date,asset_code,side_code) DO UPDATE SET
                      timeframe_code=excluded.timeframe_code,trades=excluded.trades,winners=excluded.winners,
                      mae_q80_atr=excluded.mae_q80_atr,mfe_q70_atr=excluded.mfe_q70_atr,
                      current_stop_atr=excluded.current_stop_atr,current_take_atr=excluded.current_take_atr,
                      current_volume_ratio=excluded.current_volume_ratio,
                      recommended_stop_atr=excluded.recommended_stop_atr,
                      recommended_take_atr=excluded.recommended_take_atr,
                      recommended_volume_ratio=excluded.recommended_volume_ratio,
                      recommendation_status=excluded.recommendation_status,reason_code=excluded.reason_code,
                      payload=excluded.payload,generated_at=excluded.generated_at
                    """,
                    (profile.asset,side,TIMEFRAMES[profile.asset],result["trades"],result["winners"],
                     result["mae_q80_atr"],result["mfe_q70_atr"],profile.min_stop_atr,profile.target_atr,
                     profile.min_volume_ratio,result["recommended_stop_atr"],result["recommended_take_atr"],
                     result["recommended_volume_ratio"],result["status"],result["reason"],json.dumps(payload)),
                )
                print("FUTURES_RISK_CALIBRATION", profile.asset, side, result)
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
