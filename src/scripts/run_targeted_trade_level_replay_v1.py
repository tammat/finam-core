from __future__ import annotations

import os
import statistics
import uuid

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window
from scripts.build_strategy_execution_runner_v1 import Bar, build_trades
from scripts.run_relative_strength_parameter_adapter_v2 import TARGETS, build_rows
from scripts.run_intermarket_lead_lag_parameter_adapter_v2 import RELATIONSHIPS, relationship_rows
from scripts.run_strategy_hypothesis_execution_pipeline_v2 import STRATEGY_CODES, normalized_params


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "TARGETED_TRADE_LEVEL_REPLAY_V1"
PRICE_FAMILIES = {"MOMENTUM", "BREAKOUT", "MEAN_REVERSION"}


def metric(values: list[float]) -> tuple[int, float, float]:
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value <= 0]
    loss = abs(sum(losses))
    return len(values), sum(wins) / loss if loss else 0.0, statistics.fmean(values) if values else 0.0


def main() -> None:
    require_off_market_research_window("TARGETED_TRADE_LEVEL_REPLAY_V1")
    replay_run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT attribution_run_id,execution_run_id FROM analytics.trial_gross_net_attribution_v1
                ORDER BY created_at DESC LIMIT 1""")
            source = cur.fetchone()
            cur.execute("""SELECT a.trial_id,a.hypothesis_id,a.strategy_family,r.parameter_json
                FROM analytics.trial_gross_net_attribution_v1 a
                JOIN analytics.hypothesis_trial_registry_v2 t ON t.trial_id=a.trial_id
                JOIN analytics.strategy_hypothesis_execution_result_v2 r
                  ON r.execution_run_id=t.execution_run_id AND r.candidate_hash=t.candidate_hash
                WHERE a.attribution_run_id=%s AND a.diagnosis_code='EDGE_DESTROYED_BY_COSTS'
                ORDER BY a.strategy_family,a.trial_id""", (source["attribution_run_id"],))
            candidates = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.targeted_trade_level_replay_v1 (
                    replay_run_id uuid NOT NULL, source_attribution_run_id uuid NOT NULL,
                    trial_id uuid NOT NULL, hypothesis_id uuid NOT NULL, strategy_family text NOT NULL,
                    replayed_trades integer NOT NULL, gross_profit_factor numeric NOT NULL,
                    gross_expectancy numeric NOT NULL, total_cost numeric NOT NULL,
                    net_profit_factor numeric NOT NULL, net_expectancy numeric NOT NULL,
                    replay_status text NOT NULL, source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(replay_run_id,trial_id)
                );
            """)
            cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol='IMOEX' AND timeframe='M5' ORDER BY ts")
            price_bars = [Bar(row["ts"], float(row["close"])) for row in cur.fetchall() if row["close"]]
            validation_end = int(len(price_bars) * 0.75)
            price_cost = statistics.median(bar.close for bar in price_bars) * 8.0 / 10000.0

            all_symbols = sorted({"IMOEX", "IMOEX2", *TARGETS, *(x for pair in RELATIONSHIPS for x in pair[:2])})
            cur.execute("""SELECT symbol,ts,close FROM public.market_bars WHERE timeframe='M5'
                AND symbol=ANY(%s) AND close IS NOT NULL ORDER BY ts""", (all_symbols,))
            series: dict[str, dict] = {symbol: {} for symbol in all_symbols}
            for row in cur.fetchall():
                series[row["symbol"]][row["ts"]] = float(row["close"])

            for candidate in candidates:
                family = candidate["strategy_family"]
                params = candidate["parameter_json"]
                gross_values: list[float] = []
                net_values: list[float] = []
                if family in PRICE_FAMILIES:
                    normalized = normalized_params(family, params)
                    normalized.update({"commission": price_cost, "slippage": 0.0})
                    lookback = normalized["lookback"]
                    run = {"strategy_code": STRATEGY_CODES[family], "parameter_json": normalized}
                    trades = [trade for trade in build_trades(run, price_bars[validation_end-lookback:])
                              if trade.entry_ts >= price_bars[validation_end].ts]
                    direction = params.get("direction")
                    if direction:
                        side = "BUY" if direction == "LONG" else "SELL"
                        trades = [trade for trade in trades if trade.side == side]
                    gross_values = [trade.gross_pnl for trade in trades]
                    net_values = [trade.net_pnl for trade in trades]
                elif family == "RELATIVE_STRENGTH":
                    rows = build_rows(series, str(params["benchmark"]), params)
                    entry_times = sorted({row[0] for row in rows})
                    oos_start = entry_times[int(len(entry_times) * 0.75)]
                    net_values = [row[2] for row in rows if row[0] >= oos_start]
                    gross_values = [value + 8.0 for value in net_values]
                else:
                    for source_symbol, target_symbol, direction in RELATIONSHIPS:
                        rows, timestamps = relationship_rows(series, source_symbol, target_symbol, direction, params)
                        if len(timestamps) < 100:
                            continue
                        oos_start = timestamps[int(len(timestamps) * 0.75)]
                        values = [row[2] for row in rows if row[0] >= oos_start]
                        net_values.extend(values)
                        gross_values.extend(value + 8.0 for value in values)
                trades, gross_pf, gross_exp = metric(gross_values)
                _, net_pf, net_exp = metric(net_values)
                total_cost = sum(gross_values) - sum(net_values)
                cur.execute("""INSERT INTO analytics.targeted_trade_level_replay_v1
                    (replay_run_id,source_attribution_run_id,trial_id,hypothesis_id,strategy_family,
                     replayed_trades,gross_profit_factor,gross_expectancy,total_cost,net_profit_factor,
                     net_expectancy,replay_status,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'COMPLETE',%s)""",
                    (replay_run_id,source["attribution_run_id"],candidate["trial_id"],candidate["hypothesis_id"],family,
                     trades,gross_pf,gross_exp,total_cost,net_pf,net_exp,SOURCE_VERSION))

    print(f"replay_run_id={replay_run_id}")
    print(f"source_attribution_run_id={source['attribution_run_id']}")
    print(f"targeted_candidates={len(candidates)}")
    print("verdicts_changed=0")
    print("final_holdout_opened=0")
    print("paper_created=0")
    print("live_allowed=0")
    print("VERDICT=TARGETED_TRADE_LEVEL_REPLAY_V1_OK")


if __name__ == "__main__":
    main()
