#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_EXECUTION_RUNNER_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/016_strategy_execution_runner_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.research_trade_v1 (
    id BIGSERIAL PRIMARY KEY,
    run_uuid UUID NOT NULL,
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    trade_no INTEGER NOT NULL,
    side TEXT NOT NULL,
    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,
    entry_price NUMERIC(20,8) NOT NULL DEFAULT 0,
    exit_price NUMERIC(20,8) NOT NULL DEFAULT 0,
    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_EXECUTION_RUNNER_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_uuid, trade_no)
);

CREATE INDEX IF NOT EXISTS ix_research_trade_v1_run_uuid
ON analytics.research_trade_v1(run_uuid);

CREATE INDEX IF NOT EXISTS ix_research_trade_v1_strategy_symbol
ON analytics.research_trade_v1(strategy_code, symbol, timeframe);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.research_trade_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat > src/scripts/build_strategy_execution_runner_v1.py <<'PY'
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
RUNNER_VERSION = "STRATEGY_EXECUTION_RUNNER_V1"
SCORE_FORMULA_VERSION = "EDGE_SCORE_ENGINE_PENDING"


@dataclass(frozen=True)
class Bar:
    ts: Any
    close: float


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


def safe_float(v: Any) -> float:
    if v is None:
        return 0.0
    return float(v)


def discover_bar_table(cur) -> tuple[str, str, str, str, str | None] | None:
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
            return schema, table, ts_col, close_col, tf_col
    return None


def load_bars(cur, run: dict[str, Any]) -> list[Bar]:
    found = discover_bar_table(cur)
    if not found:
        return []

    schema, table, ts_col, close_col, tf_col = found

    where = [sql.SQL("{} = %s").format(sql.Identifier("symbol"))]
    params: list[Any] = [run["symbol"]]

    if tf_col:
        where.append(sql.SQL("{} = %s").format(sql.Identifier(tf_col)))
        params.append(run["timeframe"])

    q = sql.SQL("""
        SELECT {ts_col} AS ts, {close_col} AS close
        FROM {schema}.{table}
        WHERE {where}
          AND {close_col} IS NOT NULL
        ORDER BY {ts_col} ASC
        LIMIT %s
    """).format(
        ts_col=sql.Identifier(ts_col),
        close_col=sql.Identifier(close_col),
        schema=sql.Identifier(schema),
        table=sql.Identifier(table),
        where=sql.SQL(" AND ").join(where),
    )

    params.append(MAX_BARS)
    cur.execute(q, params)

    bars = [Bar(r["ts"], safe_float(r["close"])) for r in cur.fetchall()]
    return [b for b in bars if b.close > 0]


def strategy_family(code: str) -> str:
    c = code.upper()
    if "MEAN" in c or "RSI" in c or "BOLLINGER" in c or "VWAP" in c:
        return "MEAN_REVERSION"
    if "MOMENTUM" in c or "IMPULSE" in c:
        return "MOMENTUM"
    return "BREAKOUT"


def build_trades(run: dict[str, Any], bars: list[Bar]) -> list[Trade]:
    if len(bars) < 60:
        return []

    params = run.get("parameter_json") or {}
    lookback = int(params.get("lookback", 20))
    hold = int(params.get("hold", 5))
    threshold = float(params.get("threshold", 1.0))
    commission = float(params.get("commission", 0.0))
    slippage = float(params.get("slippage", 0.0))

    family = strategy_family(run["strategy_code"])
    trades: list[Trade] = []
    i = max(lookback, 20)

    while i + hold < len(bars):
        window = [b.close for b in bars[i - lookback:i]]
        close = bars[i].close
        side = 0

        if family == "BREAKOUT":
            if close > max(window):
                side = 1
            elif close < min(window):
                side = -1
        elif family == "MOMENTUM":
            prev = bars[i - lookback].close
            if close > prev:
                side = 1
            elif close < prev:
                side = -1
        else:
            mean = statistics.fmean(window)
            stdev = statistics.pstdev(window) or 1.0
            z = (close - mean) / stdev
            if z <= -threshold:
                side = 1
            elif z >= threshold:
                side = -1

        if side == 0:
            i += 1
            continue

        entry = bars[i]
        exit_bar = bars[i + hold]
        gross = (exit_bar.close - entry.close) * side
        net = gross - commission - slippage
        trades.append(Trade(
            no=len(trades) + 1,
            side="BUY" if side > 0 else "SELL",
            entry_ts=entry.ts,
            exit_ts=exit_bar.ts,
            entry_price=entry.close,
            exit_price=exit_bar.close,
            gross_pnl=gross,
            commission=commission,
            slippage=slippage,
            net_pnl=net,
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
            cur.execute("""
                SELECT *
                FROM analytics.edge_lab_run_v1
                WHERE status_code='QUEUED'
                ORDER BY created_at ASC, id ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED;
            """, (LIMIT,))
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
                    trades = build_trades(run, bars)
                    m = metrics(trades)
                    elapsed_ms = int((time.perf_counter() - start) * 1000)

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

    print("=== STRATEGY_EXECUTION_RUNNER_V1 ===")
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
        print("VERDICT=STRATEGY_EXECUTION_RUNNER_V1_FAILED")
        raise SystemExit(1)

    print("VERDICT=STRATEGY_EXECUTION_RUNNER_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "strategy.execution.runner.title": "Strategy Execution Runner",
        "strategy.execution.runner.subtitle": "Прогон исследовательских стратегий по историческим данным с записью trade set.",
        "edge.verdict.NO_MARKET_DATA": "Нет рыночных данных"
    })
except NameError:
    pass
PY

cat > scripts/test_strategy_execution_runner_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_EXECUTION_RUNNER_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/016_strategy_execution_runner_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_strategy_execution_runner_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core STRATEGY_EXECUTION_RUNNER_LIMIT=10 PYTHONPATH=src \
python src/scripts/build_strategy_execution_runner_v1.py | tee /tmp/strategy_execution_runner_v1.txt

grep -q "VERDICT=STRATEGY_EXECUTION_RUNNER_V1_READY" /tmp/strategy_execution_runner_v1.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
done_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='DONE';")
trade_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.research_trade_v1') IS NOT NULL;")
failed_runs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_lab_run_v1 WHERE status_code='FAILED';")

test "$obs" -gt 0
test "$done_runs" -gt 0
test "$trade_table" = "t"
test "$failed_runs" = "0"

grep -q "strategy.execution.runner.title" src/marketcore/presentation/ui_labels.py
grep -q "edge.verdict.NO_MARKET_DATA" src/marketcore/presentation/ui_labels.py

echo "observations=$obs"
echo "done_runs=$done_runs"
echo "trade_table=$trade_table"
echo "failed_runs=$failed_runs"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_EXECUTION_RUNNER_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_execution_runner_v1.sh
scripts/test_strategy_execution_runner_v1.sh

echo "VERDICT=BUILD_STRATEGY_EXECUTION_RUNNER_V1_OK"
