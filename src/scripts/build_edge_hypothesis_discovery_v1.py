from __future__ import annotations

import json
import os
import statistics
import uuid
from collections import defaultdict

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, metrics


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_HYPOTHESIS_DISCOVERY_V2_TRUSTED_BARS"
MIN_BARS = int(os.getenv("EDGE_HYPOTHESIS_MIN_BARS", "6000"))
MAX_MARKETS = int(os.getenv("EDGE_HYPOTHESIS_MAX_MARKETS", "12"))


def load_search_configuration(cursor):
    cursor.execute("""
        SELECT algorithm_code,strategy_code,parameter_grid,regime_policy,gate_policy,config_version
        FROM analytics.edge_search_algorithm_registry_v1
        WHERE enabled ORDER BY algorithm_code
    """)
    rows = cursor.fetchall()
    if not rows:
        raise RuntimeError("EDGE_SEARCH_ALGORITHM_CONFIG_MISSING")
    result = {}
    for row in rows:
        family = row["algorithm_code"]
        grid = row["parameter_grid"]
        if not grid:
            raise RuntimeError(f"EDGE_SEARCH_PARAMETER_GRID_EMPTY:{family}")
        result[family] = {
            "strategy_code": row["strategy_code"], "grid": grid,
            "regime_policy": row["regime_policy"], "gate_policy": row["gate_policy"],
            "config_version": row["config_version"],
        }
    return result


def regime_map(bars: list[Bar], start: int) -> dict[object, str]:
    changes = [abs((bars[i].close / bars[i - 1].close) - 1.0) for i in range(max(1, start), len(bars))]
    median_vol = statistics.median(changes) if changes else 0.0
    result = {}
    for i in range(max(40, start), len(bars)):
        trend = ((bars[i].close / bars[i - 40].close) - 1.0) * 100.0
        one_bar_vol = abs((bars[i].close / bars[i - 1].close) - 1.0)
        if trend >= 1.0:
            regime = "TREND_UP"
        elif trend <= -1.0:
            regime = "TREND_DOWN"
        else:
            regime = "RANGE_HIGH_VOL" if one_bar_vol >= median_vol else "RANGE_LOW_VOL"
        result[bars[i].ts] = regime
    return result


def score(pf: float, expectancy: float, trades: int, folds: int, regimes: int) -> float:
    return round(min(100.0,
        min(40.0, max(0.0, (pf - 1.0) * 50.0))
        + min(20.0, max(0.0, expectancy * 4.0))
        + min(15.0, trades / 4.0)
        + folds * 5.0
        + regimes * 5.0
    ), 6)


def pnl_metrics(values: list[float]) -> dict[str, float]:
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value <= 0]
    gross_loss = abs(sum(losses))
    return {
        "trades": len(values),
        "profit_factor": sum(wins) / gross_loss if gross_loss else 0.0,
        "expectancy": statistics.fmean(values) if values else 0.0,
    }


def main() -> None:
    run_id = uuid.uuid4()
    results = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT symbol,timeframe,count(*) AS bars
                FROM public.market_bars
                WHERE timeframe='M5'
                  AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
                GROUP BY symbol,timeframe
                HAVING count(*) >= %s
                ORDER BY count(*) DESC
                LIMIT %s
            """, (MIN_BARS, MAX_MARKETS))
            markets = cur.fetchall()
            configurations = load_search_configuration(cur)

            for market in markets:
                cur.execute("SELECT ts,close,coalesce(volume,0) AS volume FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL AND source NOT IN ('unknown','synthetic_futures_backfill_v1') ORDER BY ts", (market["symbol"], market["timeframe"]))
                bars = [Bar(row["ts"], float(row["close"]), float(row["volume"])) for row in cur.fetchall()]
                train_end = int(len(bars) * 0.50)
                validation_end = int(len(bars) * 0.75)
                regimes = regime_map(bars, validation_end)
                crypto = str(market["symbol"]).endswith("USD")
                cost_bps = 20.0 if crypto else 8.0
                reference_price = statistics.median(bar.close for bar in bars)
                roundtrip_cost = reference_price * cost_bps / 10000.0

                for family, configuration in configurations.items():
                    strategy_code, grid = configuration["strategy_code"], configuration["grid"]
                    for base_params in grid:
                        params = {**base_params, "commission": roundtrip_cost, "slippage": 0.0}
                        lookback = int(params["lookback"])
                        run = {"strategy_code": strategy_code, "parameter_json": params}
                        validation_start_ts = bars[train_end].ts
                        oos_start_ts = bars[validation_end].ts
                        validation_trades = [
                            trade for trade in build_trades(run, bars[train_end - lookback:validation_end])
                            if trade.entry_ts >= validation_start_ts
                        ]
                        oos_trades = [
                            trade for trade in build_trades(run, bars[validation_end - lookback:])
                            if trade.entry_ts >= oos_start_ts
                        ]
                        validation = metrics(validation_trades)
                        oos = metrics(oos_trades)

                        fold_passes = 0
                        if oos_trades:
                            fold_span = max(1, (len(bars) - validation_end) // 3)
                            for fold_no in range(3):
                                start = validation_end + fold_no * fold_span
                                end = len(bars) if fold_no == 2 else min(len(bars), start + fold_span)
                                fold_values = [trade for trade in oos_trades if bars[start].ts <= trade.entry_ts <= bars[end - 1].ts]
                                fold = metrics(fold_values)
                                fold_passes += int(fold["trades"] >= 8 and fold["profit_factor"] >= 1.0 and fold["expectancy"] > 0)

                        by_regime = defaultdict(list)
                        for trade in oos_trades:
                            by_regime[regimes.get(trade.entry_ts, "UNKNOWN")].append(trade.net_pnl)
                        regime_metrics = {name: pnl_metrics(values) for name, values in by_regime.items()}
                        profitable_regimes = sum(1 for item in regime_metrics.values() if item["trades"] >= 5 and item["profit_factor"] > 1.0 and item["expectancy"] > 0)

                        passed = (
                            validation["trades"] >= 30 and validation["profit_factor"] >= 1.05 and validation["expectancy"] > 0
                            and oos["trades"] >= 30 and oos["profit_factor"] >= 1.10 and oos["expectancy"] > 0
                            and fold_passes >= 2 and profitable_regimes >= 2
                        )
                        hypothesis_score = score(oos["profit_factor"], oos["expectancy"], oos["trades"], fold_passes, profitable_regimes)
                        verdict = "OOS_PASS" if passed else "OOS_FAIL"
                        cur.execute("""
                            INSERT INTO analytics.edge_hypothesis_result_v1 (
                                discovery_run_id,strategy_family,strategy_code,symbol,timeframe,parameter_json,market_regimes,
                                validation_trades,validation_profit_factor,validation_expectancy,oos_trades,oos_profit_factor,
                                oos_expectancy,oos_max_drawdown,folds_passed,profitable_regimes,transaction_cost_bps,
                                hypothesis_score,verdict_code,promotion_allowed,source_version
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s)
                        """, (str(run_id), family, strategy_code, market["symbol"], market["timeframe"], psycopg2.extras.Json(base_params), psycopg2.extras.Json(regime_metrics),
                              validation["trades"], validation["profit_factor"], validation["expectancy"], oos["trades"], oos["profit_factor"],
                              oos["expectancy"], oos["max_drawdown"], fold_passes, profitable_regimes, cost_bps,
                              hypothesis_score, verdict, SOURCE_VERSION))
                        results.append((hypothesis_score, family, market["symbol"], base_params, verdict))

    results.sort(reverse=True, key=lambda item: item[0])
    print(f"discovery_run_id={run_id}")
    print(f"markets={len(markets)}")
    print(f"hypotheses={len(results)}")
    print(f"oos_pass={sum(1 for row in results if row[4] == 'OOS_PASS')}")
    print(f"oos_fail={sum(1 for row in results if row[4] == 'OOS_FAIL')}")
    for rank, row in enumerate(results[:10], start=1):
        print(f"top_{rank}={row[1]}|{row[2]}|score={row[0]}|verdict={row[4]}|params={json.dumps(row[3], sort_keys=True)}")
    print("promotion_allowed=0")
    print("runtime_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_HYPOTHESIS_DISCOVERY_V1_READY")


if __name__ == "__main__":
    main()
