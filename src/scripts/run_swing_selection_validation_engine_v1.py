from __future__ import annotations

import math
import os
import statistics
import uuid
from statistics import NormalDist

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SWING_SELECTION_VALIDATION_ENGINE_V1"
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


def trade_rows(family, params, timestamps, prices, source_prices=None):
    rows = []
    lookback = int(params.get("lookback", params.get("impulse_bars", 10)))
    hold = int(params.get("holding_bars", 3))
    lag = int(params.get("lag_bars", 0))
    for i in range(lookback, len(timestamps)-lag-hold):
        ts = timestamps[i]
        entry_i = i + lag
        exit_i = entry_i + hold
        side = 0
        if family == "MOMENTUM":
            change = prices[i] / prices[i-lookback] - 1.0
            required = 1 if params["direction"] == "LONG" else -1
            side = required if change * required > 0 else 0
        elif family == "BREAKOUT":
            window = prices[i-lookback:i]
            side = 1 if prices[i] > max(window) else (-1 if prices[i] < min(window) else 0)
        elif family == "RELATIVE_STRENGTH":
            target_change = prices[i] / prices[i-lookback] - 1.0
            source_change = source_prices[i] / source_prices[i-lookback] - 1.0
            relative = target_change - source_change
            side = 1 if relative > 0 else (-1 if relative < 0 else 0)
        else:
            impulse = source_prices[i] / source_prices[i-lookback] - 1.0
            side = 1 if impulse > 0 else (-1 if impulse < 0 else 0)
        if side:
            pnl = (prices[exit_i] / prices[entry_i] - 1.0) * 10000.0 * side - COST_BPS
            rows.append((timestamps[entry_i], pnl))
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
                cur.execute("""SELECT symbol,ts,close FROM analytics.swing_market_bars_v1
                    WHERE timeframe=%s AND symbol=ANY(%s) AND ts<%s ORDER BY ts""",(c["timeframe"],symbols,c["final_oos_start"]))
                data={s:{} for s in symbols}
                for r in cur.fetchall(): data[r["symbol"]][r["ts"]]=float(r["close"])
                timestamps=sorted(set(data[c["symbol"]]).intersection(*(set(data[s]) for s in symbols[1:]))) if source else sorted(data[c["symbol"]])
                prices=[data[c["symbol"]][ts] for ts in timestamps]
                source_prices=[data[source][ts] for ts in timestamps] if source else None
                rows=trade_rows(c["strategy_family"],c["parameter_json"],timestamps,prices,source_prices)
                selection=[r for r in rows if c["train_end"]<=r[0]<c["selection_end"]]
                validation=[r for r in rows if c["selection_end"]<=r[0]<=c["validation_end"]]
                st,spf,sexp=metrics(selection); vt,vpf,vexp=metrics(validation)
                mid=len(validation)//2
                folds=sum(int(metrics(part)[2]>0 and metrics(part)[1]>=1.0) for part in (validation[:mid],validation[mid:]) if part)
                p=adjusted_p(validation,len(candidates))
                ok=st>=20 and spf>=1.05 and sexp>0 and vt>=15 and vpf>=1.05 and vexp>0 and folds==2 and p<=0.05
                status="VALIDATION_PASS" if ok else "VALIDATION_FAIL"
                reason="PASS" if ok else "SWING_SELECTION_VALIDATION_GATE_FAILED"
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
