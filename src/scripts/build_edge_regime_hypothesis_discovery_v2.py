from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import load_search_configuration, score
from scripts.build_strategy_execution_runner_v1 import Bar, Trade, build_trades, metrics
from scripts.edge_research_universe_v1 import load_research_universe
from scripts.meta_entry_policy_v2 import apply_meta_entry_policy_v2, load_meta_entry_policy_v2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "REGIME_AWARE_EDGE_DISCOVERY_V5_RESUMABLE"
MIN_BARS = int(os.getenv("EDGE_HYPOTHESIS_MIN_BARS", "6000"))
FRESHNESS_MINUTES = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", "15"))
MIN_CONFIDENCE = float(os.getenv("EDGE_REGIME_MIN_CONFIDENCE", "0.60"))
MIN_COVERAGE = float(os.getenv("EDGE_REGIME_MIN_COVERAGE", "0.80"))
BATCH_SECONDS = max(30, int(os.getenv("EDGE_REGIME_BATCH_SECONDS", "600")))
PROGRESS_HEARTBEAT_SECONDS = max(
    5, int(os.getenv("EDGE_REGIME_PROGRESS_HEARTBEAT_SECONDS", "15"))
)
MAX_TASK_ATTEMPTS = max(1, int(os.getenv("EDGE_REGIME_MAX_TASK_ATTEMPTS", "3")))


@dataclass
class MarketContext:
    bars: list[Bar]
    strategy_bars: dict[str, list[Bar]]
    entry_policy: dict
    regime_by_ts: dict[object, str]
    source_by_ts: dict[object, str]
    confidence_by_ts: dict[object, float]
    coverage: float
    train_end: int
    validation_end: int
    validation_start_ts: object
    oos_start_ts: object
    roundtrip_cost: float
    cost_bps: float


def _json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"NOT_JSON_SERIALIZABLE:{type(value).__name__}")


def _attach_reference(
    cur, bars: list[Bar], symbol: str | None, timeframe: str, cutoff_ts: datetime
) -> list[Bar]:
    if not symbol:
        return bars
    cur.execute(
        """SELECT ts,close FROM public.market_bars
        WHERE symbol=%s AND timeframe=%s AND ts<=%s
          AND close IS NOT NULL AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
        ORDER BY ts""",
        (symbol, timeframe, cutoff_ts),
    )
    reference = {row["ts"]: float(row["close"]) for row in cur.fetchall()}
    return [Bar(bar.ts, bar.close, bar.volume, reference.get(bar.ts)) for bar in bars]


def _filtered(trades: list[Trade], regime_by_ts: dict[object, str], regime: str) -> list[Trade]:
    return [trade for trade in trades if regime_by_ts.get(trade.entry_ts) == regime]


def _fold_passes(trades: list[Trade], bars: list[Bar], start_index: int, gate: dict) -> int:
    if not trades:
        return 0
    fold_span = max(1, (len(bars) - start_index) // 3)
    passed = 0
    for fold_no in range(3):
        start = start_index + fold_no * fold_span
        end = len(bars) if fold_no == 2 else min(len(bars), start + fold_span)
        fold = metrics(
            [trade for trade in trades if bars[start].ts <= trade.entry_ts <= bars[end - 1].ts]
        )
        passed += int(
            fold["trades"] >= gate["fold_min_trades"]
            and fold["profit_factor"] >= gate["fold_min_profit_factor"]
            and fold["expectancy"] > gate["fold_min_expectancy"]
        )
    return passed


def _latest_running_campaign(cur) -> dict | None:
    cur.execute(
        """SELECT * FROM analytics.edge_regime_discovery_run_v3
        WHERE status_code='RUNNING' AND source_version=%s
        ORDER BY started_at DESC LIMIT 1""",
        (SOURCE_VERSION,),
    )
    return cur.fetchone()


def _create_campaign(cur) -> dict:
    run_id = uuid.uuid4()
    scenario_run_id = os.getenv("EDGE_SEARCH_SCENARIO_RUN_ID")
    cur.execute("SELECT clock_timestamp() AS cutoff_ts")
    cutoff_ts = cur.fetchone()["cutoff_ts"]
    markets = load_research_universe(
        cur,
        run_id=str(run_id),
        stage_code="DISCOVERY",
        min_bars=MIN_BARS,
        freshness_minutes=FRESHNESS_MINUTES,
    )
    configurations = load_search_configuration(cur)
    tasks: list[tuple] = []
    task_order = 0
    for market in markets:
        market_spec = {
            "symbol": market["symbol"],
            "timeframe": market["timeframe"],
            "contract_root": market.get("contract_root"),
            "expiration_date": market.get("expiration_date"),
        }
        for family, configuration in configurations:
            targets = configuration["regime_policy"].get("target_symbols", [])
            if targets and market["symbol"] not in targets:
                continue
            configuration_spec = {
                "regime_policy": configuration["regime_policy"],
                "gate_policy": configuration["gate_policy"],
                "config_version": configuration["config_version"],
            }
            for base_params in configuration["grid"]:
                task_order += 1
                tasks.append(
                    (
                        str(uuid.uuid4()),
                        str(run_id),
                        task_order,
                        market["symbol"],
                        market["timeframe"],
                        family,
                        configuration["strategy_code"],
                        json.dumps(market_spec, default=_json_default),
                        json.dumps(configuration_spec, default=_json_default),
                        json.dumps(base_params, default=_json_default),
                    )
                )
    cur.execute(
        """INSERT INTO analytics.edge_regime_discovery_run_v3(
            discovery_run_id,scenario_run_id,status_code,source_version,data_cutoff_ts,
            markets_total,tasks_total)
        VALUES(%s,%s,'RUNNING',%s,%s,%s,%s)""",
        (str(run_id), scenario_run_id, SOURCE_VERSION, cutoff_ts, len(markets), len(tasks)),
    )
    if tasks:
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO analytics.edge_regime_discovery_task_v3(
                task_id,discovery_run_id,task_order,symbol,timeframe,strategy_family,
                strategy_code,market_spec,configuration_spec,base_params) VALUES %s""",
            tasks,
            template="(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)",
            page_size=500,
        )
    return {
        "discovery_run_id": str(run_id),
        "data_cutoff_ts": cutoff_ts,
        "markets_total": len(markets),
        "tasks_total": len(tasks),
    }


def _load_market_context(cur, task: dict, cutoff_ts: datetime) -> MarketContext:
    market = task["market_spec"]
    expiration_date = market.get("expiration_date")
    cur.execute(
        """SELECT ts,close,coalesce(volume,0) AS volume
        FROM public.market_bars
        WHERE symbol=%s AND timeframe=%s AND ts<=%s
          AND close IS NOT NULL
          AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
          AND (%s IS NULL OR ts < %s::date + interval '1 day')
        ORDER BY ts""",
        (task["symbol"], task["timeframe"], cutoff_ts, expiration_date, expiration_date),
    )
    bars = [Bar(row["ts"], float(row["close"]), float(row["volume"])) for row in cur.fetchall()]
    if len(bars) < MIN_BARS:
        raise RuntimeError(f"EDGE_REGIME_BARS_INSUFFICIENT:{task['symbol']}:{len(bars)}")
    entry_policy = load_meta_entry_policy_v2(cur, task["symbol"], task["timeframe"], bars)
    cur.execute(
        """SELECT DISTINCT ON (ts) ts,regime,confidence,source
        FROM analytics_regime_snapshots_v2
        WHERE symbol=%s AND timeframe=%s AND ts<=%s AND confidence >= %s
        ORDER BY ts,confidence DESC,updated_at DESC""",
        (task["symbol"], task["timeframe"], cutoff_ts, MIN_CONFIDENCE),
    )
    snapshots = cur.fetchall()
    regime_by_ts = {row["ts"]: row["regime"] for row in snapshots}
    source_by_ts = {row["ts"]: row["source"] for row in snapshots}
    confidence_by_ts = {row["ts"]: float(row["confidence"]) for row in snapshots}
    coverage = len(set(regime_by_ts).intersection(bar.ts for bar in bars)) / len(bars)
    train_end = int(len(bars) * 0.50)
    validation_end = int(len(bars) * 0.75)
    cost_bps = 20.0 if str(task["symbol"]).endswith("USD") else 8.0
    roundtrip_cost = statistics.median(bar.close for bar in bars) * cost_bps / 10000.0
    return MarketContext(
        bars=bars,
        strategy_bars={},
        entry_policy=entry_policy,
        regime_by_ts=regime_by_ts,
        source_by_ts=source_by_ts,
        confidence_by_ts=confidence_by_ts,
        coverage=coverage,
        train_end=train_end,
        validation_end=validation_end,
        validation_start_ts=bars[train_end].ts,
        oos_start_ts=bars[validation_end].ts,
        roundtrip_cost=roundtrip_cost,
        cost_bps=cost_bps,
    )


def _execute_task(cur, task: dict, context: MarketContext, cutoff_ts: datetime) -> tuple[int, int, int]:
    configuration = task["configuration_spec"]
    reference_symbol = configuration["regime_policy"].get("reference_symbol")
    cache_key = reference_symbol or ""
    if cache_key not in context.strategy_bars:
        context.strategy_bars[cache_key] = _attach_reference(
            cur, context.bars, reference_symbol, task["timeframe"], cutoff_ts
        )
    strategy_bars = context.strategy_bars[cache_key]
    allowed_regimes = configuration["regime_policy"].get("allowed_regimes")
    if not allowed_regimes:
        raise RuntimeError(f"REGIME_POLICY_ALLOWED_REGIMES_MISSING:{task['strategy_family']}")
    base_params = apply_meta_entry_policy_v2(dict(task["base_params"]), context.entry_policy)
    market = task["market_spec"]
    params = {
        **base_params,
        "commission": context.roundtrip_cost,
        "slippage": 0.0,
        "contract_symbol": task["symbol"] if market.get("expiration_date") else None,
        "contract_root": market.get("contract_root"),
        "contract_expiration": market.get("expiration_date"),
        "reference_symbol": reference_symbol,
    }
    lookback = int(params["lookback"])
    run = {"strategy_code": task["strategy_code"], "parameter_json": params}
    validation_all = [
        trade
        for trade in build_trades(
            run, strategy_bars[context.train_end - lookback : context.validation_end]
        )
        if trade.entry_ts >= context.validation_start_ts
    ]
    oos_all = [
        trade
        for trade in build_trades(run, strategy_bars[context.validation_end - lookback :])
        if trade.entry_ts >= context.oos_start_ts
    ]
    cur.execute(
        "DELETE FROM analytics.edge_regime_hypothesis_result_v2 WHERE discovery_task_id=%s",
        (task["task_id"],),
    )
    pass_count = unverified_count = 0
    for regime in allowed_regimes:
        validation_trades = _filtered(validation_all, context.regime_by_ts, regime)
        oos_trades = _filtered(oos_all, context.regime_by_ts, regime)
        validation = metrics(validation_trades)
        oos = metrics(oos_trades)
        regime_gate = configuration["gate_policy"]["regime"]
        folds = _fold_passes(oos_trades, context.bars, context.validation_end, regime_gate)
        observed_ts = [trade.entry_ts for trade in validation_trades + oos_trades]
        trust_status = "VERIFIED" if context.coverage >= MIN_COVERAGE and observed_ts else "UNVERIFIED"
        validation_gate = configuration["gate_policy"]["validation"]
        oos_gate = configuration["gate_policy"]["oos"]
        passed = (
            trust_status == "VERIFIED"
            and validation["trades"] >= validation_gate["min_trades"]
            and validation["profit_factor"] >= validation_gate["min_profit_factor"]
            and validation["expectancy"] > validation_gate["min_expectancy"]
            and oos["trades"] >= oos_gate["min_trades"]
            and oos["profit_factor"] >= oos_gate["min_profit_factor"]
            and oos["expectancy"] > oos_gate["min_expectancy"]
            and folds >= regime_gate["min_folds_passed"]
        )
        verdict = "OOS_PASS" if passed else ("UNVERIFIED" if trust_status == "UNVERIFIED" else "OOS_FAIL")
        reason = "PASS" if passed else ("INSUFFICIENT_REGIME_COVERAGE" if trust_status == "UNVERIFIED" else "REGIME_OOS_GATE_FAILED")
        hypothesis_score = score(
            oos["profit_factor"], oos["expectancy"], oos["trades"], folds, int(bool(oos_trades))
        )
        sources = sorted(
            {context.source_by_ts[ts] for ts in observed_ts if ts in context.source_by_ts}
        )
        min_confidence = min(
            (context.confidence_by_ts[ts] for ts in observed_ts if ts in context.confidence_by_ts),
            default=0.0,
        )
        cur.execute(
            """INSERT INTO analytics.edge_regime_hypothesis_result_v2(
                discovery_run_id,discovery_task_id,strategy_family,strategy_code,symbol,timeframe,
                parameter_json,regime_code,regime_source,min_regime_confidence,regime_coverage_ratio,
                validation_trades,validation_profit_factor,validation_expectancy,oos_trades,
                oos_profit_factor,oos_expectancy,oos_max_drawdown,folds_passed,folds_total,
                transaction_cost_bps,hypothesis_score,trust_status,verdict_code,reason_code,
                promotion_allowed,source_version)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,%s,%s,%s,%s,%s,false,%s)""",
            (
                task["discovery_run_id"],
                task["task_id"],
                task["strategy_family"],
                task["strategy_code"],
                task["symbol"],
                task["timeframe"],
                psycopg2.extras.Json(base_params),
                regime,
                ",".join(sources) or "NONE",
                min_confidence,
                context.coverage,
                validation["trades"],
                validation["profit_factor"],
                validation["expectancy"],
                oos["trades"],
                oos["profit_factor"],
                oos["expectancy"],
                oos["max_drawdown"],
                folds,
                context.cost_bps,
                hypothesis_score,
                trust_status,
                verdict,
                reason,
                SOURCE_VERSION,
            ),
        )
        pass_count += int(passed)
        unverified_count += int(trust_status == "UNVERIFIED")
    return len(allowed_regimes), pass_count, unverified_count


def _refresh_campaign_totals(cur, discovery_run_id: str) -> dict:
    cur.execute(
        """SELECT count(*) FILTER(WHERE status_code='COMPLETE') completed,
                  count(*) FILTER(WHERE status_code='FAILED') failed,
                  count(*) total,coalesce(sum(results_written),0) results,
                  coalesce(sum(pass_count),0) passes
        FROM analytics.edge_regime_discovery_task_v3 WHERE discovery_run_id=%s""",
        (discovery_run_id,),
    )
    totals = cur.fetchone()
    progress = int(100 * totals["completed"] / totals["total"]) if totals["total"] else 100
    status = "FAILED" if totals["failed"] else ("COMPLETE" if totals["completed"] == totals["total"] else "RUNNING")
    cur.execute(
        """UPDATE analytics.edge_regime_discovery_run_v3 SET
            status_code=%s,tasks_completed=%s,results_total=%s,oos_pass=%s,progress_pct=%s,
            heartbeat_at=clock_timestamp(),finished_at=CASE WHEN %s='COMPLETE' THEN clock_timestamp() ELSE NULL END
        WHERE discovery_run_id=%s""",
        (status, totals["completed"], totals["results"], totals["passes"], progress, status, discovery_run_id),
    )
    return {**totals, "progress": progress, "status": status}


def main() -> None:
    started = time.monotonic()
    last_progress_refresh = started
    processed_this_batch = 0
    unverified_this_batch = 0
    conn = psycopg2.connect(DB)
    try:
        # Each completed parameter task is its own durable checkpoint. CPU work
        # never holds an obsolete snapshot transaction open.
        conn.autocommit = True
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (741903127,))
            campaign = _latest_running_campaign(cur)
            if campaign is None:
                campaign = _create_campaign(cur)
            discovery_run_id = str(campaign["discovery_run_id"])
            cutoff_ts = campaign["data_cutoff_ts"]
            cur.execute(
                """UPDATE analytics.edge_regime_discovery_task_v3
                SET status_code='PENDING',error_text=concat_ws(E'\n',error_text,'RECOVERED_AFTER_PROCESS_STOP')
                WHERE discovery_run_id=%s AND status_code='RUNNING'""",
                (discovery_run_id,),
            )
            context_cache: dict[tuple[str, str], MarketContext] = {}
            while time.monotonic() - started < BATCH_SECONDS:
                cur.execute(
                    """SELECT * FROM analytics.edge_regime_discovery_task_v3
                    WHERE discovery_run_id=%s AND status_code='PENDING'
                    ORDER BY task_order LIMIT 1""",
                    (discovery_run_id,),
                )
                task = cur.fetchone()
                if task is None:
                    break
                cur.execute(
                    """UPDATE analytics.edge_regime_discovery_task_v3 SET
                        status_code='RUNNING',attempts=attempts+1,started_at=coalesce(started_at,clock_timestamp()),
                        heartbeat_at=clock_timestamp(),error_text=NULL WHERE task_id=%s""",
                    (task["task_id"],),
                )
                try:
                    cache_key = (task["symbol"], task["timeframe"])
                    if cache_key not in context_cache:
                        context_cache[cache_key] = _load_market_context(cur, task, cutoff_ts)
                    written, passes, unverified = _execute_task(
                        cur, task, context_cache[cache_key], cutoff_ts
                    )
                    cur.execute(
                        """UPDATE analytics.edge_regime_discovery_task_v3 SET
                            status_code='COMPLETE',results_written=%s,pass_count=%s,
                            heartbeat_at=clock_timestamp(),finished_at=clock_timestamp()
                        WHERE task_id=%s""",
                        (written, passes, task["task_id"]),
                    )
                    processed_this_batch += 1
                    unverified_this_batch += unverified
                except Exception as exc:
                    attempts = int(task["attempts"]) + 1
                    failed = attempts >= MAX_TASK_ATTEMPTS
                    cur.execute(
                        """UPDATE analytics.edge_regime_discovery_task_v3 SET
                            status_code=%s,error_text=%s,heartbeat_at=clock_timestamp(),
                            finished_at=CASE WHEN %s THEN clock_timestamp() ELSE NULL END
                        WHERE task_id=%s""",
                        ("FAILED" if failed else "PENDING", str(exc)[:4000], failed, task["task_id"]),
                    )
                    if failed:
                        cur.execute(
                            """UPDATE analytics.edge_regime_discovery_run_v3 SET
                                status_code='FAILED',error_text=%s,heartbeat_at=clock_timestamp(),
                                finished_at=clock_timestamp() WHERE discovery_run_id=%s""",
                            (str(exc)[:4000], discovery_run_id),
                        )
                        raise
                if time.monotonic() - last_progress_refresh >= PROGRESS_HEARTBEAT_SECONDS:
                    _refresh_campaign_totals(cur, discovery_run_id)
                    last_progress_refresh = time.monotonic()
            totals = _refresh_campaign_totals(cur, discovery_run_id)
            cur.execute("SELECT pg_advisory_unlock(%s)", (741903127,))
    finally:
        conn.close()

    print(f"discovery_run_id={discovery_run_id}")
    print(f"markets={campaign['markets_total']}")
    print(f"freshness_minutes={FRESHNESS_MINUTES}")
    print(f"tasks_total={totals['total']}")
    print(f"tasks_completed={totals['completed']}")
    print(f"tasks_processed={processed_this_batch}")
    print(f"campaign_progress_pct={totals['progress']}")
    print(f"strategy_regime_pairs={totals['results']}")
    print(f"oos_pass={totals['passes']}")
    print(f"unverified={unverified_this_batch}")
    print(f"stage_complete={int(totals['status'] == 'COMPLETE')}")
    print("promotion_allowed=0")
    print("VERDICT=REGIME_AWARE_EDGE_DISCOVERY_V2_READY")


if __name__ == "__main__":
    main()
