from __future__ import annotations

import json
import math
import os
import statistics
import uuid
from statistics import NormalDist

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, metrics


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "STRATEGY_HYPOTHESIS_EXECUTION_PIPELINE_V2"
PRICE_FAMILIES = {"MOMENTUM", "BREAKOUT", "MEAN_REVERSION"}
STRATEGY_CODES = {
    "MOMENTUM": "MOMENTUM_CONTINUATION_V2",
    "BREAKOUT": "VOLATILITY_BREAKOUT_V2",
    "MEAN_REVERSION": "MEAN_REVERSION_V2",
}


def normalized_params(family: str, raw: dict) -> dict:
    threshold = raw.get("threshold", raw.get("entry_zscore", 1.0))
    if family == "MOMENTUM":
        threshold = float(threshold) * 100.0
    return {
        "lookback": int(raw.get("lookback", 20)),
        "hold": int(raw.get("holding_bars", 5)),
        "threshold": float(threshold),
    }


def p_value(trades) -> float:
    values = [trade.net_pnl for trade in trades]
    if len(values) < 2:
        return 1.0
    stdev = statistics.stdev(values)
    if stdev <= 0:
        return 1.0
    z = statistics.fmean(values) / (stdev / math.sqrt(len(values)))
    return max(0.0, min(1.0, 1.0 - NormalDist().cdf(z)))


def fold_passes(trades, bars: list[Bar], start: int) -> int:
    span = max(1, (len(bars) - start) // 3)
    passed = 0
    for no in range(3):
        left = start + no * span
        right = len(bars) if no == 2 else min(len(bars), left + span)
        subset = [trade for trade in trades if bars[left].ts <= trade.entry_ts <= bars[right - 1].ts]
        result = metrics(subset)
        passed += int(result["trades"] >= 8 and result["profit_factor"] >= 1.0 and result["expectancy"] > 0)
    return passed


def main() -> None:
    execution_run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT parameter_space_run_id FROM analytics.hypothesis_parameter_space_v2
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            if not latest:
                raise RuntimeError("NO_PARAMETER_SPACE_V2")
            parameter_run_id = latest["parameter_space_run_id"]
            cur.execute("""SELECT strategy_family,parameter_json,candidate_hash,engine_code
                FROM analytics.hypothesis_parameter_space_v2 WHERE parameter_space_run_id=%s AND enabled=true
                ORDER BY strategy_family,candidate_hash""", (parameter_run_id,))
            candidates = [dict(row) for row in cur.fetchall()]
            total = len(candidates)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.strategy_hypothesis_execution_run_v2 (
                    execution_run_id uuid PRIMARY KEY, parameter_space_run_id uuid NOT NULL,
                    total_candidates integer NOT NULL, processed_candidates integer NOT NULL DEFAULT 0,
                    oos_pass integer NOT NULL DEFAULT 0, oos_fail integer NOT NULL DEFAULT 0,
                    unverified integer NOT NULL DEFAULT 0, status text NOT NULL,
                    live_allowed boolean NOT NULL DEFAULT false, source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz
                );
                CREATE TABLE IF NOT EXISTS analytics.strategy_hypothesis_execution_result_v2 (
                    execution_run_id uuid NOT NULL REFERENCES analytics.strategy_hypothesis_execution_run_v2(execution_run_id),
                    candidate_hash text NOT NULL, strategy_family text NOT NULL, engine_code text NOT NULL,
                    symbol text, timeframe text, parameter_json jsonb NOT NULL,
                    validation_trades integer NOT NULL DEFAULT 0, validation_profit_factor numeric NOT NULL DEFAULT 0,
                    oos_trades integer NOT NULL DEFAULT 0, oos_profit_factor numeric NOT NULL DEFAULT 0,
                    oos_expectancy numeric NOT NULL DEFAULT 0, folds_passed integer NOT NULL DEFAULT 0,
                    adjusted_p_value numeric NOT NULL DEFAULT 1, verdict_code text NOT NULL,
                    reason_code text NOT NULL, promotion_allowed boolean NOT NULL DEFAULT false,
                    source_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(execution_run_id,candidate_hash)
                );
            """)
            cur.execute("""INSERT INTO analytics.strategy_hypothesis_execution_run_v2
                (execution_run_id,parameter_space_run_id,total_candidates,status,source_version)
                VALUES (%s,%s,%s,'RUNNING',%s)""", (execution_run_id, parameter_run_id, total, SOURCE_VERSION))

            cur.execute("""SELECT symbol,timeframe,count(*) bars FROM public.market_bars
                WHERE timeframe='M5' GROUP BY symbol,timeframe HAVING count(*) >= 6000
                ORDER BY CASE WHEN symbol='IMOEX' THEN 0 ELSE 1 END,count(*) DESC LIMIT 1""")
            market = cur.fetchone()
            cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s ORDER BY ts",
                        (market["symbol"], market["timeframe"]))
            bars = [Bar(row["ts"], float(row["close"])) for row in cur.fetchall() if row["close"]]
            train_end = int(len(bars) * 0.50)
            validation_end = int(len(bars) * 0.75)
            reference_price = statistics.median(bar.close for bar in bars)
            cost = reference_price * 8.0 / 10000.0
            passed = failed = unverified = 0

            for candidate in candidates:
                family = candidate["strategy_family"]
                raw = candidate["parameter_json"]
                verdict = "UNVERIFIED"
                reason = "ENGINE_PARAMETER_ADAPTER_PENDING"
                validation = {"trades": 0, "profit_factor": 0.0}
                oos = {"trades": 0, "profit_factor": 0.0, "expectancy": 0.0}
                folds = 0
                adjusted = 1.0
                if family in PRICE_FAMILIES:
                    params = normalized_params(family, raw)
                    params.update({"commission": cost, "slippage": 0.0})
                    lookback = params["lookback"]
                    run = {"strategy_code": STRATEGY_CODES[family], "parameter_json": params}
                    validation_trades = [t for t in build_trades(run, bars[train_end-lookback:validation_end]) if t.entry_ts >= bars[train_end].ts]
                    oos_trades = [t for t in build_trades(run, bars[validation_end-lookback:]) if t.entry_ts >= bars[validation_end].ts]
                    direction = raw.get("direction")
                    if direction:
                        side = "BUY" if direction == "LONG" else "SELL"
                        validation_trades = [t for t in validation_trades if t.side == side]
                        oos_trades = [t for t in oos_trades if t.side == side]
                    validation = metrics(validation_trades)
                    oos = metrics(oos_trades)
                    folds = fold_passes(oos_trades, bars, validation_end)
                    adjusted = min(1.0, p_value(oos_trades) * total)
                    is_pass = (validation["trades"] >= 30 and validation["profit_factor"] >= 1.05
                               and oos["trades"] >= 30 and oos["profit_factor"] >= 1.10
                               and oos["expectancy"] > 0 and folds >= 2 and adjusted <= 0.05)
                    verdict = "OOS_PASS" if is_pass else "OOS_FAIL"
                    reason = "PASS" if is_pass else "STRICT_OOS_OR_MULTIPLE_TESTING_GATE_FAILED"
                passed += int(verdict == "OOS_PASS")
                failed += int(verdict == "OOS_FAIL")
                unverified += int(verdict == "UNVERIFIED")
                cur.execute("""INSERT INTO analytics.strategy_hypothesis_execution_result_v2
                    (execution_run_id,candidate_hash,strategy_family,engine_code,symbol,timeframe,parameter_json,
                     validation_trades,validation_profit_factor,oos_trades,oos_profit_factor,oos_expectancy,
                     folds_passed,adjusted_p_value,verdict_code,reason_code,promotion_allowed,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s)""",
                    (execution_run_id,candidate["candidate_hash"],family,candidate["engine_code"],market["symbol"],market["timeframe"],
                     psycopg2.extras.Json(raw),validation["trades"],validation["profit_factor"],oos["trades"],oos["profit_factor"],
                     oos["expectancy"],folds,adjusted,verdict,reason,SOURCE_VERSION))
            cur.execute("""UPDATE analytics.strategy_hypothesis_execution_run_v2 SET
                processed_candidates=%s,oos_pass=%s,oos_fail=%s,unverified=%s,status='COMPLETE',completed_at=now()
                WHERE execution_run_id=%s""", (total, passed, failed, unverified, execution_run_id))

    print(f"execution_run_id={execution_run_id}")
    print(f"parameter_candidates={total}")
    print(f"processed={total}")
    print(f"oos_pass={passed}")
    print(f"oos_fail={failed}")
    print(f"unverified={unverified}")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=STRATEGY_HYPOTHESIS_EXECUTION_PIPELINE_V2_OK")


if __name__ == "__main__":
    main()
