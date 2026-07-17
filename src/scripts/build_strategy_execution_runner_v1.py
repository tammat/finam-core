from __future__ import annotations

import json
import math
import os
import statistics
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("STRATEGY_EXECUTION_RUNNER_LIMIT", "20"))
MAX_BARS = int(os.getenv("STRATEGY_EXECUTION_MAX_BARS", "5000"))
RESEARCH_BATCH_ID = os.getenv("STRATEGY_EXECUTION_RESEARCH_BATCH_ID")
RUNNER_VERSION = "STRATEGY_EXECUTION_RUNNER_V3_REALISTIC_EXECUTION"
ENGINE_NAME = "STRATEGY_EXECUTION_RUNNER_V3_REALISTIC_EXECUTION"
SCORE_FORMULA_VERSION = "EDGE_SCORE_ENGINE_PENDING"


@dataclass(frozen=True)
class Bar:
    ts: Any
    close: float
    volume: float = 0.0
    reference_close: float | None = None
    best_bid: float | None = None
    best_ask: float | None = None


@dataclass(frozen=True)
class Trade:
    no: int
    side: str
    entry_ts: Any
    exit_ts: Any
    entry_price: float
    exit_price: float
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    quantity: float = 1.0
    fill_ratio: float = 1.0
    spread_cost: float = 0.0
    impact_cost: float = 0.0
    latency_bars: int = 0
    quote_source: str = "LEGACY"
    capacity_rub: float = 0.0
    contract_spec_source: str = "LEGACY"


def safe_float(v: Any) -> float:
    if v is None:
        return 0.0
    return float(v)


DEFAULT_EXECUTION_POLICY = {
    "policy_code": "REALISTIC_EXECUTION_V1",
    "signal_latency_bars": 1,
    "max_participation_rate": 0.01,
    "minimum_fill_ratio": 0.25,
    "target_notional_rub": 100000.0,
    "fallback_spread_bps": 8.0,
    "impact_bps_at_max_participation": 4.0,
    "stress_cost_multiplier": 1.5,
}


def load_execution_context(cur, symbol: str) -> dict[str, Any]:
    """Load one immutable policy plus empirical liquidity and contract metadata."""
    policy = dict(DEFAULT_EXECUTION_POLICY)
    cur.execute("""SELECT policy_code,policy FROM analytics.execution_simulation_policy_v1
        WHERE active ORDER BY activated_at DESC LIMIT 1""")
    row = cur.fetchone()
    if row:
        policy.update(row["policy"] or {})
        policy["policy_code"] = row["policy_code"]

    cur.execute("""SELECT lot_size,tick_size,contract_multiplier,source_version
        FROM analytics.market_contract_spec_v1
        WHERE is_active AND (symbol=%s OR
          (%s LIKE 'BR%%@RTSX' AND symbol='BR@RTSX') OR
          (%s LIKE 'NG%%@RTSX' AND symbol='NG@RTSX'))
        ORDER BY (symbol=%s) DESC,valid_from DESC LIMIT 1""", (symbol,symbol,symbol,symbol))
    spec = cur.fetchone()
    policy.update({
        "lot_size": float(spec["lot_size"]) if spec else 1.0,
        "tick_size": float(spec["tick_size"]) if spec else 0.0,
        "contract_multiplier": float(spec["contract_multiplier"]) if spec else 1.0,
        "contract_spec_source": spec["source_version"] if spec else "MISSING_SPEC_FALLBACK",
    })

    cur.execute("""WITH recent AS (
          SELECT spread_bps FROM analytics.market_microstructure_snapshot_v1
          WHERE symbol=%s AND spread_bps>0 ORDER BY observed_at DESC LIMIT 10000
        ) SELECT percentile_cont(0.90) WITHIN GROUP (ORDER BY spread_bps)::float8 spread_bps,
                 count(*) samples FROM recent""", (symbol,))
    quote = cur.fetchone()
    if quote and int(quote["samples"] or 0) >= 100:
        policy["fallback_spread_bps"] = max(
            float(policy["fallback_spread_bps"]), float(quote["spread_bps"])
        )
        policy["quote_source"] = "EMPIRICAL_P90_MICROSTRUCTURE"
        policy["quote_samples"] = int(quote["samples"])
    else:
        policy["quote_source"] = "POLICY_FALLBACK"
        policy["quote_samples"] = int(quote["samples"] or 0) if quote else 0
    return policy


def discover_bar_table(cur) -> tuple[str, str, str, str, str | None, str | None, str | None] | None:
    candidates = [
        ("analytics", "market_bars"),
        ("public", "market_bars"),
        ("analytics", "market_bar_v1"),
        ("analytics", "market_bars_v1"),
        ("public", "candles"),
        ("analytics", "candles"),
        ("analytics", "ohlcv"),
        ("public", "ohlcv"),
    ]

    cur.execute("""
        SELECT table_schema, table_name, column_name
        FROM information_schema.columns
        WHERE table_schema IN ('analytics','public')
    """)
    cols: dict[tuple[str, str], set[str]] = {}
    for r in cur.fetchall():
        key = (r["table_schema"], r["table_name"])
        cols.setdefault(key, set()).add(r["column_name"])

    for schema, table in candidates + sorted(cols):
        c = cols.get((schema, table), set())
        if not c:
            continue
        symbol_col = "symbol" if "symbol" in c else None
        close_col = "close" if "close" in c else None
        ts_col = next((x for x in ["bar_ts", "ts", "timestamp", "datetime", "time", "created_at"] if x in c), None)
        tf_col = next((x for x in ["timeframe", "tf", "interval"] if x in c), None)
        if symbol_col and close_col and ts_col:
            volume_col = "volume" if "volume" in c else None
            source_col = "source" if "source" in c else None
            return schema, table, ts_col, close_col, tf_col, volume_col, source_col
    return None


def load_bars(cur, run: dict[str, Any]) -> list[Bar]:
    found = discover_bar_table(cur)
    if not found:
        return []

    schema, table, ts_col, close_col, tf_col, volume_col, source_col = found

    where = [sql.SQL("{} = %s").format(sql.Identifier("symbol"))]
    params: list[Any] = [run["symbol"]]

    if tf_col:
        where.append(sql.SQL("{} = %s").format(sql.Identifier(tf_col)))
        params.append(run["timeframe"])
    if source_col:
        where.append(sql.SQL("{} NOT IN ('unknown','synthetic_futures_backfill_v1')").format(sql.Identifier(source_col)))

    q = sql.SQL("""
        SELECT {ts_col} AS ts, {close_col} AS close, {volume_col} AS volume
        FROM {schema}.{table}
        WHERE {where}
          AND {close_col} IS NOT NULL
        ORDER BY {ts_col} DESC
        LIMIT %s
    """).format(
        ts_col=sql.Identifier(ts_col),
        close_col=sql.Identifier(close_col),
        volume_col=sql.Identifier(volume_col) if volume_col else sql.SQL("0"),
        schema=sql.Identifier(schema),
        table=sql.Identifier(table),
        where=sql.SQL(" AND ").join(where),
    )

    params.append(MAX_BARS)
    cur.execute(q, params)

    bars = [Bar(r["ts"], safe_float(r["close"]), safe_float(r["volume"])) for r in reversed(cur.fetchall())]
    return [b for b in bars if b.close > 0]


def strategy_family(code: str) -> str:
    c = code.upper()
    if "MEAN" in c or "RSI" in c or "BOLLINGER" in c or "VWAP" in c:
        return "MEAN_REVERSION"
    if "MOMENTUM" in c or "IMPULSE" in c or "EMA_TREND" in c:
        return "MOMENTUM"
    return "BREAKOUT"


def _rsi(closes: list[float]) -> float:
    if len(closes) < 2:
        return 50.0
    changes = [current - previous for previous, current in zip(closes, closes[1:])]
    average_gain = statistics.fmean(max(change, 0.0) for change in changes)
    average_loss = statistics.fmean(max(-change, 0.0) for change in changes)
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    return 100.0 - (100.0 / (1.0 + average_gain / average_loss))


def _mean_reversion_side(code: str, bars: list[Bar], index: int, lookback: int, threshold: float) -> int:
    window = bars[index - lookback:index]
    closes = [bar.close for bar in window]
    close = bars[index].close

    if code == "RSI_MEAN_REVERSION_V1":
        value = _rsi(closes + [close])
        return 1 if value <= threshold else (-1 if value >= 100.0 - threshold else 0)

    if code == "VWAP_REVERSION_V2":
        total_volume = sum(max(bar.volume, 0.0) for bar in window)
        if total_volume <= 0:
            return 0
        center = sum(bar.close * max(bar.volume, 0.0) for bar in window) / total_volume
    else:  # BOLLINGER_REVERSION_V1 and the audited legacy mean-reversion formula.
        center = statistics.fmean(closes)

    stdev = statistics.pstdev(closes)
    if stdev <= 0:
        return 0
    z_score = (close - center) / stdev
    return 1 if z_score <= -threshold else (-1 if z_score >= threshold else 0)


def _ema(values: list[float], period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    value = values[0]
    for current in values[1:]:
        value = alpha * current + (1.0 - alpha) * value
    return value


def _orthogonal_side(code: str, bars: list[Bar], index: int, params: dict[str, Any]) -> int | None:
    threshold = float(params.get("threshold", 1.0))
    if code == "EMA_TREND_FILTER_V1":
        fast = int(params.get("fast", 10))
        slow = int(params.get("slow", 40))
        closes = [bar.close for bar in bars[index - slow:index + 1]]
        volatility = statistics.pstdev(closes)
        if volatility <= 0:
            return 0
        strength = (_ema(closes[-fast:], fast) - _ema(closes, slow)) / volatility
        return 1 if strength >= threshold else (-1 if strength <= -threshold else 0)
    if code == "VOLATILITY_SCALED_MOMENTUM_V1":
        lookback = int(params.get("lookback", 40))
        vol_lookback = int(params.get("vol_lookback", 20))
        changes = [
            (bars[position].close / bars[position - 1].close) - 1.0
            for position in range(index - vol_lookback + 1, index + 1)
        ]
        volatility = statistics.pstdev(changes)
        if volatility <= 0:
            return 0
        scaled = ((bars[index].close / bars[index - lookback].close) - 1.0) / (volatility * math.sqrt(lookback))
        return 1 if scaled >= threshold else (-1 if scaled <= -threshold else 0)
    if code == "DONCHIAN_VOLATILITY_BREAKOUT_V1":
        lookback = int(params.get("lookback", 40))
        window = [bar.close for bar in bars[index - lookback:index]]
        buffer = statistics.pstdev(window) * threshold
        close = bars[index].close
        return 1 if close > max(window) + buffer else (-1 if close < min(window) - buffer else 0)
    if code == "RELATIVE_STRENGTH_V1":
        lookback = int(params.get("lookback", 40))
        current_reference = bars[index].reference_close
        previous_reference = bars[index - lookback].reference_close
        if not current_reference or not previous_reference:
            return 0
        own_return = (bars[index].close / bars[index - lookback].close) - 1.0
        reference_return = (current_reference / previous_reference) - 1.0
        relative_pct = (own_return - reference_return) * 100.0
        return 1 if relative_pct >= threshold else (-1 if relative_pct <= -threshold else 0)
    if code == "INTERMARKET_SPREAD_REVERSION_V1":
        lookback = int(params.get("lookback", 40))
        ratios = [
            math.log(bar.close / bar.reference_close)
            for bar in bars[index - lookback:index + 1]
            if bar.reference_close and bar.close > 0
        ]
        if len(ratios) != lookback + 1:
            return 0
        center = statistics.fmean(ratios[:-1])
        deviation = statistics.pstdev(ratios[:-1])
        if deviation <= 0:
            return 0
        z_score = (ratios[-1] - center) / deviation
        return -1 if z_score >= threshold else (1 if z_score <= -threshold else 0)
    return None


def build_trades(run: dict[str, Any], bars: list[Bar]) -> list[Trade]:
    if len(bars) < 60:
        return []

    params = run.get("parameter_json") or {}
    lookback = int(params.get("lookback", 20))
    hold = int(params.get("hold", 5))
    threshold = float(params.get("threshold", 1.0))
    commission = float(params.get("commission", 0.0))
    slippage = float(params.get("slippage", 0.0))
    explicit_execution_policy = bool(params.get("execution_policy"))
    execution = {**DEFAULT_EXECUTION_POLICY, **(params.get("execution_policy") or {})}
    latency = max(1, int(execution["signal_latency_bars"]))
    participation_limit = max(0.0, float(execution["max_participation_rate"]))
    minimum_fill = min(1.0, max(0.0, float(execution["minimum_fill_ratio"])))
    target_notional = max(0.0, float(execution["target_notional_rub"]))
    spread_bps = max(0.0, float(execution["fallback_spread_bps"]))
    impact_at_limit = max(0.0, float(execution["impact_bps_at_max_participation"]))
    lot_size = max(float(execution.get("lot_size", 1.0)), 1e-12)
    multiplier = max(float(execution.get("contract_multiplier", 1.0)), 1e-12)

    strategy_code = str(run["strategy_code"]).upper()
    family = strategy_family(strategy_code)
    trades: list[Trade] = []
    required_history = max(lookback, int(params.get("slow", 0)), int(params.get("vol_lookback", 0)), 20)
    i = required_history

    while i + latency + hold < len(bars):
        window = [b.close for b in bars[i - lookback:i]]
        close = bars[i].close
        side = 0

        orthogonal_side = _orthogonal_side(strategy_code, bars, i, params)
        if orthogonal_side is not None:
            side = orthogonal_side

        elif family == "BREAKOUT":
            if close > max(window):
                side = 1
            elif close < min(window):
                side = -1
        elif family == "MOMENTUM":
            prev = bars[i - lookback].close
            momentum_pct = ((close - prev) / prev) * 100.0
            if momentum_pct >= threshold:
                side = 1
            elif momentum_pct <= -threshold:
                side = -1
        else:
            side = _mean_reversion_side(strategy_code, bars, i, lookback, threshold)

        if side == 0:
            i += 1
            continue

        entry = bars[i + latency]
        exit_bar = bars[i + latency + hold]
        requested = math.floor((target_notional / (entry.close * multiplier)) / lot_size) * lot_size
        available = max(entry.volume, 0.0) * participation_limit
        if not explicit_execution_policy:
            requested = max(lot_size, requested)
            available = max(requested, available)
        filled = math.floor(min(requested, available) / lot_size) * lot_size if requested > 0 else 0.0
        fill_ratio = min(1.0, filled / requested) if requested > 0 else 0.0
        if filled <= 0 or fill_ratio < minimum_fill:
            i += 1
            continue
        actual_participation = filled / max(entry.volume, filled)
        participation_fraction = min(1.0, actual_participation / participation_limit) if participation_limit else 1.0
        impact_bps = impact_at_limit * math.sqrt(participation_fraction)
        gross = (exit_bar.close - entry.close) * side
        has_historical_quote = (
            entry.best_bid is not None and entry.best_ask is not None
            and exit_bar.best_bid is not None and exit_bar.best_ask is not None
            and entry.best_ask >= entry.best_bid > 0 and exit_bar.best_ask >= exit_bar.best_bid > 0
        )
        if has_historical_quote:
            crossed_entry = float(entry.best_ask if side > 0 else entry.best_bid)
            crossed_exit = float(exit_bar.best_bid if side > 0 else exit_bar.best_ask)
            spread_cost = max(0.0, gross - (crossed_exit-crossed_entry)*side)
            quote_source = "HISTORICAL_BID_ASK"
        else:
            half_spread_bps = spread_bps / 2.0
            crossed_entry = entry.close + side * entry.close * half_spread_bps / 10000.0
            crossed_exit = exit_bar.close - side * exit_bar.close * half_spread_bps / 10000.0
            spread_cost = (entry.close + exit_bar.close) * half_spread_bps / 10000.0
            quote_source = str(execution.get("quote_source", "POLICY_FALLBACK"))
        entry_impact = entry.close * impact_bps / 10000.0
        exit_impact = exit_bar.close * impact_bps / 10000.0
        executed_entry = crossed_entry + side * entry_impact
        executed_exit = crossed_exit - side * exit_impact
        impact_cost = (entry.close + exit_bar.close) * impact_bps / 10000.0
        execution_slippage = spread_cost + impact_cost + slippage
        net = gross - commission - execution_slippage
        trades.append(Trade(
            no=len(trades) + 1,
            side="BUY" if side > 0 else "SELL",
            entry_ts=entry.ts,
            exit_ts=exit_bar.ts,
            entry_price=executed_entry,
            exit_price=executed_exit,
            gross_pnl=gross,
            commission=commission,
            slippage=execution_slippage,
            net_pnl=net,
            quantity=filled,
            fill_ratio=fill_ratio,
            spread_cost=spread_cost,
            impact_cost=impact_cost,
            latency_bars=latency,
            quote_source=quote_source,
            capacity_rub=available * entry.close * multiplier,
            contract_spec_source=str(execution.get("contract_spec_source", "MISSING_SPEC_FALLBACK")),
        ))
        i += hold

    return trades


def drawdown(pnls: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return max_dd


def metrics(trades: list[Trade]) -> dict[str, Any]:
    pnls = [t.net_pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_win / gross_loss if gross_loss > 0 else (gross_win if gross_win > 0 else 0.0)
    exp = statistics.fmean(pnls) if pnls else 0.0
    dd = drawdown(pnls)
    recovery = sum(pnls) / abs(dd) if dd < 0 else 0.0
    stdev = statistics.pstdev(pnls) if len(pnls) > 1 else 0.0
    sharpe = exp / stdev if stdev > 0 else 0.0
    downside = [p for p in pnls if p < 0]
    down_stdev = statistics.pstdev(downside) if len(downside) > 1 else 0.0
    sortino = exp / down_stdev if down_stdev > 0 else 0.0

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "profit_factor": pf,
        "expectancy": exp,
        "avg_win": statistics.fmean(wins) if wins else 0.0,
        "avg_loss": statistics.fmean(losses) if losses else 0.0,
        "max_drawdown": dd,
        "recovery_factor": recovery,
        "sharpe": sharpe,
        "sortino": sortino,
        "commission": sum(t.commission for t in trades),
        "slippage": sum(t.slippage for t in trades),
    }


def main() -> None:
    processed = 0
    failed = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            batch_filter = "AND research_batch_id=%s" if RESEARCH_BATCH_ID else ""
            query_params = (RESEARCH_BATCH_ID, LIMIT) if RESEARCH_BATCH_ID else (LIMIT,)
            cur.execute(f"""
                SELECT *
                FROM analytics.edge_lab_run_v1
                WHERE status_code='QUEUED'
                  {batch_filter}
                ORDER BY created_at ASC, id ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED;
            """, query_params)
            runs = cur.fetchall()

            for run in runs:
                start = time.perf_counter()
                try:
                    cur.execute("""
                        UPDATE analytics.edge_lab_run_v1
                        SET status_code='RUNNING',
                            runner_version=%s,
                            started_at=now(),
                            updated_at=now()
                        WHERE id=%s
                    """, (RUNNER_VERSION, run["id"]))

                    bars = load_bars(cur, run)
                    run["parameter_json"] = {
                        **(run.get("parameter_json") or {}),
                        "execution_policy": load_execution_context(cur, run["symbol"]),
                    }
                    trades = build_trades(run, bars)
                    m = metrics(trades)
                    elapsed_ms = int((time.perf_counter() - start) * 1000)

                    cur.execute("DELETE FROM analytics.research_trade_execution_audit_v1 WHERE run_uuid=%s", (run["run_uuid"],))
                    cur.execute("DELETE FROM analytics.research_trade_v1 WHERE run_uuid=%s", (run["run_uuid"],))
                    for t in trades:
                        cur.execute("""
                            INSERT INTO analytics.research_trade_v1 (
                                run_uuid, research_code, strategy_code, symbol, timeframe,
                                trade_no, side, entry_ts, exit_ts,
                                entry_price, exit_price, gross_pnl, commission, slippage, net_pnl,
                                source_version
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            run["run_uuid"], run["research_code"], run["strategy_code"],
                            run["symbol"], run["timeframe"], t.no, t.side,
                            t.entry_ts, t.exit_ts, Decimal(str(t.entry_price)),
                            Decimal(str(t.exit_price)), Decimal(str(t.gross_pnl)),
                            Decimal(str(t.commission)), Decimal(str(t.slippage)),
                            Decimal(str(t.net_pnl)), RUNNER_VERSION,
                        ))
                        cur.execute("""INSERT INTO analytics.research_trade_execution_audit_v1
                            (run_uuid,trade_no,quantity,fill_ratio,spread_cost,impact_cost,latency_bars,
                             quote_source,capacity_rub,contract_spec_source,execution_policy_code)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT(run_uuid,trade_no) DO UPDATE SET
                              quantity=EXCLUDED.quantity,fill_ratio=EXCLUDED.fill_ratio,
                              spread_cost=EXCLUDED.spread_cost,impact_cost=EXCLUDED.impact_cost,
                              latency_bars=EXCLUDED.latency_bars,quote_source=EXCLUDED.quote_source,
                              capacity_rub=EXCLUDED.capacity_rub,
                              contract_spec_source=EXCLUDED.contract_spec_source,
                              execution_policy_code=EXCLUDED.execution_policy_code""",(
                            run["run_uuid"],t.no,Decimal(str(t.quantity)),Decimal(str(t.fill_ratio)),
                            Decimal(str(t.spread_cost)),Decimal(str(t.impact_cost)),t.latency_bars,
                            t.quote_source,Decimal(str(t.capacity_rub)),t.contract_spec_source,
                            run["parameter_json"]["execution_policy"]["policy_code"],
                        ))

                    verdict = "OBSERVED" if m["trades"] > 0 else ("NO_MARKET_DATA" if not bars else "NO_TRADES")

                    cur.execute("""
                        INSERT INTO analytics.edge_observation_v1 (
                            run_uuid, research_batch_id, research_code, strategy_code,
                            strategy_version, symbol, timeframe, parameter_hash,
                            parameter_json, dataset_version, market_data_version,
                            runner_version, score_formula_version, market_regime,
                            bars_used, trades, wins, losses, win_rate,
                            profit_factor, expectancy, avg_win, avg_loss,
                            max_drawdown, recovery_factor, sharpe, sortino,
                            ulcer_index, commission, slippage, stability_score,
                            raw_edge_score, normalized_edge_score, confidence_score,
                            research_cost_score, research_cpu_ms, research_memory_mb,
                            research_elapsed_ms, verdict_code, source_version, updated_at
                        )
                        VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,'default',
                            %s,%s,'UNKNOWN',
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,
                            %s,%s,%s,%s,
                            0,%s,%s,0,
                            0,0,0,
                            0,%s,0,%s,%s,%s,now()
                        )
                        ON CONFLICT(run_uuid) DO UPDATE SET
                            bars_used=EXCLUDED.bars_used,
                            trades=EXCLUDED.trades,
                            wins=EXCLUDED.wins,
                            losses=EXCLUDED.losses,
                            win_rate=EXCLUDED.win_rate,
                            profit_factor=EXCLUDED.profit_factor,
                            expectancy=EXCLUDED.expectancy,
                            avg_win=EXCLUDED.avg_win,
                            avg_loss=EXCLUDED.avg_loss,
                            max_drawdown=EXCLUDED.max_drawdown,
                            recovery_factor=EXCLUDED.recovery_factor,
                            sharpe=EXCLUDED.sharpe,
                            sortino=EXCLUDED.sortino,
                            commission=EXCLUDED.commission,
                            slippage=EXCLUDED.slippage,
                            research_cpu_ms=EXCLUDED.research_cpu_ms,
                            research_elapsed_ms=EXCLUDED.research_elapsed_ms,
                            verdict_code=EXCLUDED.verdict_code,
                            runner_version=EXCLUDED.runner_version,
                            source_version=EXCLUDED.source_version,
                            updated_at=now();
                    """, (
                        run["run_uuid"], run["research_batch_id"], run["research_code"],
                        run["strategy_code"], run["strategy_version"], run["symbol"],
                        run["timeframe"], run["parameter_hash"],
                        json.dumps(run["parameter_json"] or {}, ensure_ascii=False, sort_keys=True),
                        run["dataset_version"], RUNNER_VERSION, SCORE_FORMULA_VERSION,
                        len(bars), m["trades"], m["wins"], m["losses"], m["win_rate"],
                        m["profit_factor"], m["expectancy"], m["avg_win"], m["avg_loss"],
                        m["max_drawdown"], m["recovery_factor"], m["sharpe"], m["sortino"],
                        m["commission"], m["slippage"],
                        elapsed_ms, elapsed_ms, verdict, RUNNER_VERSION,
                    ))

                    cur.execute("""
                        UPDATE analytics.edge_lab_run_v1
                        SET status_code='DONE',
                            finished_at=now(),
                            runner_version=%s,
                            updated_at=now()
                        WHERE id=%s
                    """, (RUNNER_VERSION, run["id"]))

                    cur.execute("""
                        UPDATE analytics.research_queue_v1
                        SET status_code='DONE',
                            attempts=attempts + 1,
                            updated_at=now()
                        WHERE research_code=%s
                    """, (run["research_code"],))

                    processed += 1

                except Exception as exc:
                    failed += 1
                    cur.execute("""
                        UPDATE analytics.edge_lab_run_v1
                        SET status_code='FAILED',
                            finished_at=now(),
                            updated_at=now()
                        WHERE id=%s
                    """, (run["id"],))
                    cur.execute("""
                        UPDATE analytics.research_queue_v1
                        SET status_code='FAILED',
                            attempts=attempts + 1,
                            last_error=%s,
                            updated_at=now()
                        WHERE research_code=%s
                    """, (str(exc)[:1000], run["research_code"]))

            cur.execute("""
                SELECT count(*) AS observations_total,
                       count(*) FILTER (WHERE trades > 0) AS with_trades,
                       count(*) FILTER (WHERE verdict_code='NO_MARKET_DATA') AS no_market_data,
                       count(*) FILTER (WHERE verdict_code='NO_TRADES') AS no_trades
                FROM analytics.edge_observation_v1
            """)
            obs = cur.fetchone()

            cur.execute("SELECT count(*) AS trades FROM analytics.research_trade_v1")
            trade_row = cur.fetchone()

    print(f"=== {ENGINE_NAME} ===")
    print(f"limit={LIMIT}")
    print(f"processed={processed}")
    print(f"failed={failed}")
    print(f"observations_total={obs['observations_total']}")
    print(f"observations_with_trades={obs['with_trades']}")
    print(f"no_market_data={obs['no_market_data']}")
    print(f"no_trades={obs['no_trades']}")
    print(f"research_trades={trade_row['trades']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if failed:
        print(f"VERDICT={ENGINE_NAME}_FAILED")
        raise SystemExit(1)

    print(f"VERDICT={ENGINE_NAME}_READY")


if __name__ == "__main__":
    main()
