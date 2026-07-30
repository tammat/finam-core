from __future__ import annotations

import math
import os
import statistics
import uuid
from bisect import bisect_left, bisect_right
from statistics import NormalDist

import psycopg2
import psycopg2.extras
from marketcore.research.dynamic_exit_v1 import dynamic_exit_v1, entry_allowed_v1

from marketcore.research_window_guard_v1 import require_off_market_research_window
from finam_core.research.purged_split import label_horizon_bars


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SWING_SELECTION_VALIDATION_ENGINE_V5_DB_REGIME_ROUTER"
COST_BPS = 8.0


def metrics(rows):
    values = [row[1] for row in rows]
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v <= 0]
    loss = abs(sum(losses))
    return len(values), sum(wins) / loss if loss else 0.0, statistics.fmean(values) if values else 0.0


def adjusted_p(rows, trials):
    values = [row[1] for row in rows]
    if len(values) < 2 or statistics.stdev(values) <= 0: return 1.0
    z = statistics.fmean(values) / (statistics.stdev(values) / math.sqrt(len(values)))
    return min(1.0, max(0.0, 1.0 - NormalDist().cdf(z)) * trials)


def failure_reason(st, spf, sexp, vt, vpf, vexp, folds, p):
    if st < 20: return "INSUFFICIENT_SELECTION_TRADES"
    if spf < 1.05 or sexp <= 0: return "SELECTION_EDGE_FAILED"
    if vt < 15: return "INSUFFICIENT_VALIDATION_TRADES"
    if vpf < 1.05 or vexp <= 0: return "VALIDATION_EDGE_FAILED"
    if folds < 2: return "VALIDATION_FOLDS_UNSTABLE"
    if p > 0.05: return "MULTIPLE_TESTING_SIGNIFICANCE_FAILED"
    return "PASS"


def _meta_filter(params, i, side, prices, volumes):
    if str(params.get("entry_policy_code", "NONE")) in ("META_ENTRY_V1", "META_ENTRY_V2"):
        return entry_allowed_v1(prices, volumes, i, side, params)
    trend_lookback = int(params.get("trend_lookback", 40))
    volatility_lookback = int(params.get("volatility_lookback", 20))
    required = max(trend_lookback, volatility_lookback)
    if i < required or not side:
        return False
    trend = prices[i] / prices[i-trend_lookback] - 1.0
    returns = [prices[j] / prices[j-1] - 1.0 for j in range(i-volatility_lookback+1, i+1)]
    volatility_bps = statistics.pstdev(returns) * 10000.0
    history_volume = volumes[i-volatility_lookback:i]
    mean_volume = statistics.fmean(history_volume) if history_volume else 0.0
    volume_ratio = volumes[i] / mean_volume if mean_volume > 0 else 0.0
    required_regime = str(params.get("required_regime_code", "")).upper()
    trend_floor = float(params.get("regime_trend_min_bps", 10.0)) / 10000.0
    regime_ok = (
        (required_regime == "TREND_UP" and trend >= trend_floor)
        or (required_regime == "TREND_DOWN" and trend <= -trend_floor)
        or (required_regime == "RANGE" and abs(trend) < trend_floor)
        or not required_regime
    )
    allowed_side = str(params.get("allowed_side", "BOTH")).upper()
    side_ok = allowed_side == "BOTH" or (allowed_side == "LONG" and side > 0) or (allowed_side == "SHORT" and side < 0)
    trend_side_ok = required_regime == "RANGE" or trend * side > 0
    return (
        regime_ok
        and side_ok
        and trend_side_ok
        and volatility_bps >= float(params.get("min_volatility_bps", 0.0))
        and volatility_bps <= float(params.get("max_volatility_bps", 10000.0))
        and volume_ratio >= float(params.get("min_volume_ratio", 0.0))
    )


def trade_rows(family, params, timestamps, prices, source_prices=None, volumes=None):
    rows = []
    volumes = volumes if volumes is not None else [0.0] * len(prices)
    next_entry_index = 0
    lookback = int(params.get("lookback", params.get("impulse_bars", 10)))
    hold = int(params.get("holding_bars", 3))
    dynamic_hold = int(params.get("exit_max_holding_bars", max(hold, 20)))
    maximum_hold = dynamic_hold if str(params.get("exit_policy_code", "FIXED_HOLD")) == "DYNAMIC_EXIT_V1" else hold
    lag = int(params.get("lag_bars", 0))
    for i in range(lookback, len(timestamps)-lag-maximum_hold):
        if i < next_entry_index:
            continue
        ts = timestamps[i]
        entry_i = i + lag
        exit_i = entry_i + hold
        side = 0
        if family in ("MOMENTUM", "REGIME_MOMENTUM"):
            change = prices[i] / prices[i-lookback] - 1.0
            required = 1 if params["direction"] == "LONG" else -1
            threshold = float(params.get("threshold_bps", 0.0)) / 10000.0
            side = required if change * required >= threshold and threshold >= 0 else 0
        elif family in ("BREAKOUT", "META_BREAKOUT"):
            window = prices[i-lookback:i]
            side = 1 if prices[i] > max(window) else (-1 if prices[i] < min(window) else 0)
        elif family == "SWING_MEAN_REVERSION":
            window = prices[i-lookback:i]
            mean = statistics.fmean(window)
            deviation = statistics.pstdev(window)
            zscore = (prices[i] - mean) / deviation if deviation > 0 else 0.0
            requested = str(params.get("direction", "")).upper()
            threshold = float(params.get("entry_zscore", 1.5))
            if requested == "LONG" and zscore <= -threshold:
                side = 1
            elif requested == "SHORT" and zscore >= threshold:
                side = -1
        elif family == "RELATIVE_STRENGTH":
            target_change = prices[i] / prices[i-lookback] - 1.0
            source_change = source_prices[i] / source_prices[i-lookback] - 1.0
            relative = target_change - source_change
            side = 1 if relative > 0 else (-1 if relative < 0 else 0)
        else:
            impulse = source_prices[i] / source_prices[i-lookback] - 1.0
            side = 1 if impulse > 0 else (-1 if impulse < 0 else 0)
        if family in ("REGIME_MOMENTUM", "META_BREAKOUT", "SWING_MEAN_REVERSION") and not _meta_filter(params, i, side, prices, volumes):
            side = 0
        if side:
            decision = dynamic_exit_v1(prices, entry_i, side, maximum_hold, params)
            exit_i = decision.exit_index
            pnl = (prices[exit_i] / prices[entry_i] - 1.0) * 10000.0 * side - COST_BPS
            rows.append((timestamps[entry_i], pnl))
            # One strategy instance represents one position. Signals observed
            # before its exit are correlated exposure, not independent trades.
            if not bool(params.get("allow_overlapping_positions", False)):
                next_entry_index = exit_i
    return rows


def main():
    require_off_market_research_window("SWING_SELECTION_VALIDATION_ENGINE_V1")
    run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT factory_run_id FROM analytics.swing_hypothesis_factory_v1 ORDER BY created_at DESC LIMIT 1")
            factory = cur.fetchone()
            cur.execute("SELECT * FROM analytics.swing_hypothesis_factory_v1 WHERE factory_run_id=%s ORDER BY hypothesis_id", (factory["factory_run_id"],))
            candidates = [dict(r) for r in cur.fetchall()]
            cur.execute("""CREATE TABLE IF NOT EXISTS analytics.swing_selection_validation_result_v1 (
                validation_run_id uuid NOT NULL,factory_run_id uuid NOT NULL,hypothesis_id uuid NOT NULL,
                strategy_family text NOT NULL,symbol text NOT NULL,timeframe text NOT NULL,
                selection_trades integer NOT NULL,selection_pf numeric NOT NULL,selection_expectancy numeric NOT NULL,
                validation_trades integer NOT NULL,validation_pf numeric NOT NULL,validation_expectancy numeric NOT NULL,
                validation_folds_passed integer NOT NULL,adjusted_p_value numeric NOT NULL,
                validation_status text NOT NULL,reason_code text NOT NULL,final_oos_opened boolean NOT NULL DEFAULT false,
                promotion_allowed boolean NOT NULL DEFAULT false,source_version text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(validation_run_id,hypothesis_id));""")
            passed=failed=0
            for c in candidates:
                source = c["parameter_json"].get("benchmark") or c["parameter_json"].get("source")
                symbols=[c["symbol"]]+([source] if source else [])
                cur.execute("""SELECT symbol,ts,close,coalesce(volume,0) volume FROM analytics.swing_market_bars_v1
                    WHERE timeframe=%s AND symbol=ANY(%s) AND ts<%s ORDER BY ts""",(c["timeframe"],symbols,c["final_oos_start"]))
                data={s:{} for s in symbols}; volume_data={s:{} for s in symbols}
                for r in cur.fetchall():
                    data[r["symbol"]][r["ts"]]=float(r["close"])
                    volume_data[r["symbol"]][r["ts"]]=float(r["volume"])
                timestamps=sorted(set(data[c["symbol"]]).intersection(*(set(data[s]) for s in symbols[1:]))) if source else sorted(data[c["symbol"]])
                prices=[data[c["symbol"]][ts] for ts in timestamps]
                volumes=[volume_data[c["symbol"]][ts] for ts in timestamps]
                source_prices=[data[source][ts] for ts in timestamps] if source else None
                rows=trade_rows(c["strategy_family"],c["parameter_json"],timestamps,prices,source_prices,volumes)
                horizon=label_horizon_bars(c["parameter_json"])
                train_i=bisect_left(timestamps,c["train_end"])
                selection_i=bisect_left(timestamps,c["selection_end"])
                validation_i=bisect_right(timestamps,c["validation_end"])-1
                selection_start=timestamps[min(len(timestamps)-1,train_i+horizon)]
                selection_stop=timestamps[max(0,selection_i-horizon)]
                validation_start=timestamps[min(len(timestamps)-1,selection_i+horizon)]
                validation_stop=timestamps[max(0,validation_i-horizon)]
                selection=[r for r in rows if selection_start<=r[0]<selection_stop]
                validation=[r for r in rows if validation_start<=r[0]<=validation_stop]
                st,spf,sexp=metrics(selection); vt,vpf,vexp=metrics(validation)
                mid=len(validation)//2
                folds=sum(int(metrics(part)[2]>0 and metrics(part)[1]>=1.0) for part in (validation[:mid],validation[mid:]) if part)
                p=adjusted_p(validation,len(candidates))
                ok=st>=20 and spf>=1.05 and sexp>0 and vt>=15 and vpf>=1.05 and vexp>0 and folds==2 and p<=0.05
                status="VALIDATION_PASS" if ok else "VALIDATION_FAIL"
                reason=failure_reason(st,spf,sexp,vt,vpf,vexp,folds,p)
                passed+=int(ok); failed+=int(not ok)
                cur.execute("""INSERT INTO analytics.swing_selection_validation_result_v1
                    (validation_run_id,factory_run_id,hypothesis_id,strategy_family,symbol,timeframe,
                     selection_trades,selection_pf,selection_expectancy,validation_trades,validation_pf,
                     validation_expectancy,validation_folds_passed,adjusted_p_value,validation_status,
                     reason_code,final_oos_opened,promotion_allowed,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s)""",
                    (run_id,c["factory_run_id"],c["hypothesis_id"],c["strategy_family"],c["symbol"],c["timeframe"],
                     st,spf,sexp,vt,vpf,vexp,folds,p,status,reason,SOURCE_VERSION))
    print(f"validation_run_id={run_id}"); print(f"candidates={len(candidates)}"); print(f"validation_pass={passed}"); print(f"validation_fail={failed}")
    print("final_oos_opened=0"); print("promotion_allowed=0"); print("live_allowed=0"); print("VERDICT=SWING_SELECTION_VALIDATION_ENGINE_V1_OK")

if __name__=="__main__": main()
