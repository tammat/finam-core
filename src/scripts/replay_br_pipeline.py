"""
Replay исторических BR M5/M15 баров через PAPER signal processor.
Русский комментарий: скрипт не отправляет заявки и не использует broker execution.
Он читает market_data из PostgreSQL и вызывает тот же метод pipeline,
который используется live-режимом для BR PAPER-сигналов.
"""

from __future__ import annotations

import argparse
import uuid
import os
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2

from finam_core.execution.paper_engine import PaperExecutionEngine
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.risk.finam_limits_adapter import FinamLimitsAdapter
from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.strategy.br_conservative_breakout import BrConservativeBreakout


@dataclass
class ReplayBar:
    symbol: str
    timeframe: str
    ts: datetime
    open: float
    high: float
    low: float
    close_price: float
    volume: float


@dataclass
class ReplayStats:
    bars_processed: int = 0
    m15_processed: int = 0
    m5_processed: int = 0
    signals_generated: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    risk_accepted: int = 0
    risk_rejected: int = 0
    paper_orders: int = 0
    paper_buy_orders: int = 0
    paper_sell_orders: int = 0
    trades_logged: int = 0
    position_limit_rejected: int = 0
    regime_policy_rejected: int = 0
    symbol_drawdown_rejected: int = 0
    loss_streak_rejected: int = 0
    portfolio_guard_rejected: int = 0
    other_execution_rejected: int = 0



class NullNotifier:
    """Русский комментарий: replay не должен спамить Telegram историческими сигналами."""

    def send(self, text: str) -> None:
        return None


class ReplayRuntimeConfig:
    """Русский комментарий: минимальный runtime_config adapter для replay без запуска полного pipeline.__init__."""

    def __init__(self) -> None:
        self.values = {
            "EXECUTION_MODE": os.getenv("EXECUTION_MODE", "paper"),
            "ENABLE_PAPER_FILLS": os.getenv("ENABLE_PAPER_FILLS", "1"),
            "SIMULATE_MARKET": os.getenv("SIMULATE_MARKET", "0"),
            "REAL_EXECUTION_ENABLED": "0",
            "REAL_ORDER_CONFIRM": "0",
        }

    def get(self, key: str, default=None):
        return self.values.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.values.get(key, None)
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.values.get(key, None)
        if value is None:
            return default
        try:
            return float(value)
        except Exception:
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.values.get(key, None)
        if value is None:
            return default
        try:
            return int(value)
        except Exception:
            return default


# CountingLogger wrapper for PostgresLogger
class CountingLogger:
    """Русский комментарий: обёртка над PostgresLogger для подсчёта сигналов."""

    def __init__(self, inner: PostgresLogger):
        self.inner = inner
        self.signals_total = 0
        self.buy_count = 0
        self.sell_count = 0
        self.risk_accepted_count = 0
        self.risk_rejected_count = 0
        self.trades_logged_count = 0

    def log_signal(self, **kwargs):
        self.signals_total += 1
        side = kwargs.get("side")
        if side == "BUY":
            self.buy_count += 1
        elif side == "SELL":
            self.sell_count += 1

        status = kwargs.get("status")
        if status == "risk_accepted":
            self.risk_accepted_count += 1
        elif status == "risk_rejected":
            self.risk_rejected_count += 1

        return self.inner.log_signal(**kwargs)

    def log_risk_event(self, **kwargs):
        return self.inner.log_risk_event(**kwargs)

    def log_trade(self, *args, **kwargs):
        """Русский комментарий: пишем paper-fill в trades; если PostgresLogger не совпал по сигнатуре — прямой INSERT."""
        try:
            result = self.inner.log_trade(*args, **kwargs)
            self.trades_logged_count += 1
            return result
        except Exception:
            trade = args[0] if args and isinstance(args[0], dict) else dict(kwargs)
            self._insert_trade_direct(trade)
            self.trades_logged_count += 1
            return None

    def _insert_trade_direct(self, trade: dict) -> None:
        """Русский комментарий: replay fallback под фактическую таблицу trades на Debian."""
        symbol = str(trade.get("symbol", ""))
        side = str(trade.get("side", ""))
        qty = float(trade.get("qty", trade.get("quantity", 0.0)) or 0.0)
        price = float(trade.get("price", 0.0) or 0.0)
        trade_id = str(trade.get("trade_id", f"paper_replay_{symbol}_{side}_{price}"))
        account_id = str(os.getenv("FINAM_ACCOUNT_ID", os.getenv("ACCOUNT_ID", "paper")))
        commission = float(trade.get("commission", 0.0) or 0.0)
        raw_json = dict(trade)
        raw_json.setdefault("execution_type", trade.get("execution_type", "paper_replay"))
        raw_json.setdefault("paper_only", True)

        with psycopg2.connect(dsn()) as conn:
            with conn.cursor() as cur:
                # Русский комментарий: replay/paper сделки явно маркируются trade_source='paper'.
                cur.execute(
                    """
                    INSERT INTO trades (symbol, side, qty, price, commission, fill_id, origin, payload, ts, trade_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, now(), %s)
                    """,
                    (
                        symbol,
                        side,
                        qty,
                        price,
                        commission,
                        trade_id,
                        "replay_br_pipeline",
                        json.dumps(raw_json, ensure_ascii=False, default=str),
                        "paper",
                    ),
                )

    def __getattr__(self, name):
        return getattr(self.inner, name)



class CountingPaperExecution:
    """Русский комментарий: обёртка над настоящим PaperExecutionEngine для replay-диагностики."""

    def __init__(self, inner: PaperExecutionEngine):
        self.inner = inner
        self.orders_total = 0
        self.buy_orders = 0
        self.sell_orders = 0

    def _count(self, order: dict) -> None:
        self.orders_total += 1
        side = order.get("side")
        if side == "BUY":
            self.buy_orders += 1
        elif side == "SELL":
            self.sell_orders += 1

    def execute(self, order: dict, market_state: dict | None = None):
        self._count(order)
        if hasattr(self.inner, "execute"):
            return self.inner.execute(order, market_state=market_state)
        if hasattr(self.inner, "execute_order"):
            return self.inner.execute_order(order)
        if hasattr(self.inner, "submit_order"):
            return self.inner.submit_order(order)
        return {"status": "paper_counted_only", "paper_only": True, "order": order}

    def execute_order(self, order: dict):
        return self.execute(order)

    def submit_order(self, order: dict):
        return self.execute(order)

    def __getattr__(self, name):
        return getattr(self.inner, name)




def dsn() -> str:
    """Русский комментарий: replay обязан писать в ту же БД, что и production/Grafana."""
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_DSN")
        or "postgresql://finam:finam@127.0.0.1:5432/finam_core"
    )



def parse_ts(value: str | None):
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def load_bars(symbols: list[str], from_ts=None, to_ts=None) -> list[ReplayBar]:
    """Русский комментарий: replay читает нормализованный OHLCV-источник market_bars."""
    where = [
        "symbol = ANY(%s)",
        "timeframe IN ('M15', 'M5')",
        "source = 'finam_grpc_bars_v1'",
    ]
    params: list[object] = [symbols]

    if from_ts is not None:
        where.append("ts >= %s")
        params.append(from_ts)
    if to_ts is not None:
        where.append("ts <= %s")
        params.append(to_ts)

    rows: list[ReplayBar] = []
    with psycopg2.connect(dsn()) as conn:
        sql = f"""
            SELECT
                symbol,
                timeframe,
                ts,
                open,
                high,
                low,
                close,
                volume
            FROM market_bars
            WHERE {' AND '.join(where)}
            ORDER BY ts ASC,
                     CASE WHEN timeframe = 'M15' THEN 0 WHEN timeframe = 'M5' THEN 1 ELSE 2 END ASC
        """

        with conn.cursor() as cur:
            cur.execute(sql, params)
            for symbol_v, timeframe, ts, open_p, high_p, low_p, close_p, volume in cur.fetchall():
                rows.append(
                    ReplayBar(
                        symbol=str(symbol_v),
                        timeframe=str(timeframe),
                        ts=ts,
                        open=float(open_p),
                        high=float(high_p),
                        low=float(low_p),
                        close_price=float(close_p),
                        volume=float(volume or 0.0),
                    )
                )
    return rows


def build_replay_pipeline(symbol: str, run_id: str, portfolio_guard_state: dict):
    """Русский комментарий: создаем минимальный pipeline-объект только для BR signal processor."""
    pipeline = object.__new__(PaperTradingPipeline)
    pipeline.br_breakout_enabled = True
    pipeline.br_breakout_symbol = symbol
    pipeline.br_breakout = BrConservativeBreakout(symbol=symbol)
    base_logger = PostgresLogger()
    pipeline.pg_logger = CountingLogger(base_logger)
    pipeline.notifier = NullNotifier()
    pipeline.paper = CountingPaperExecution(PaperExecutionEngine())
    pipeline.risk = None
    pipeline.run_id = run_id
    pipeline.portfolio_guard_state = portfolio_guard_state
    # Русский комментарий: replay создаёт pipeline без __init__, поэтому runtime_config задаётся вручную.
    pipeline.runtime_config = ReplayRuntimeConfig()
    pipeline.finam_limits_adapter = FinamLimitsAdapter()
    return pipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRM6@RTSX")
    parser.add_argument("--symbols", nargs="+")
    parser.add_argument("--from-ts")
    parser.add_argument("--to-ts")
    args = parser.parse_args()
    run_id = str(uuid.uuid4())
    print(f"RUN_ID={run_id}")
    portfolio_guard_state = {"paper_orders_total": 0, "positions": {}}

    symbols = args.symbols if args.symbols else [args.symbol]

    os.environ["EXECUTION_MODE"] = os.getenv("EXECUTION_MODE", "paper")
    os.environ["ENABLE_BR_CONSERVATIVE_BREAKOUT"] = "1"
    os.environ["BR_BREAKOUT_SYMBOL"] = symbols[0]

    bars = load_bars(
        symbols=symbols,
        from_ts=parse_ts(args.from_ts),
        to_ts=parse_ts(args.to_ts),
    )

    pipelines = {
        symbol: build_replay_pipeline(symbol, run_id=run_id, portfolio_guard_state=portfolio_guard_state)
        for symbol in symbols
    }
    stats = {symbol: ReplayStats() for symbol in symbols}

    for bar in bars:
        pipeline = pipelines.get(bar.symbol)
        if pipeline is None:
            continue

        symbol_stats = stats[bar.symbol]
        tf = str(bar.timeframe).upper()
        if tf == "M15":
            symbol_stats.m15_processed += 1
        elif tf == "M5":
            symbol_stats.m5_processed += 1

        pipeline._process_br_closed_bar_for_paper_signal(bar)
        symbol_stats.bars_processed += 1

    print("REPLAY_BR_PIPELINE")
    print(f"symbols={','.join(symbols)}")

    total = ReplayStats()

    for symbol in symbols:
        pipeline = pipelines[symbol]
        logger = pipeline.pg_logger
        paper = getattr(pipeline, "paper", None)
        symbol_stats = stats[symbol]

        symbol_stats.signals_generated = int(getattr(logger, "signals_total", 0))
        symbol_stats.buy_signals = int(getattr(logger, "buy_count", 0))
        symbol_stats.sell_signals = int(getattr(logger, "sell_count", 0))
        symbol_stats.risk_accepted = int(getattr(logger, "risk_accepted_count", 0))
        symbol_stats.risk_rejected = int(getattr(logger, "risk_rejected_count", 0))
        symbol_stats.paper_orders = int(getattr(paper, "orders_total", 0))
        symbol_stats.paper_buy_orders = int(getattr(paper, "buy_orders", 0))
        symbol_stats.paper_sell_orders = int(getattr(paper, "sell_orders", 0))
        symbol_stats.trades_logged = int(getattr(logger, "trades_logged_count", 0))
        symbol_stats.position_limit_rejected = int(getattr(pipeline, "_br_position_limit_rejected", 0))
        symbol_stats.regime_policy_rejected = int(getattr(pipeline, "_br_regime_policy_rejected", 0))
        symbol_stats.symbol_drawdown_rejected = int(getattr(pipeline, "_br_symbol_drawdown_rejected", 0))
        symbol_stats.loss_streak_rejected = int(getattr(pipeline, "_br_loss_streak_rejected", 0))
        symbol_stats.portfolio_guard_rejected = int(getattr(pipeline, "_br_portfolio_guard_rejected", 0))
        symbol_stats.other_execution_rejected = int(getattr(pipeline, "_br_other_execution_rejected", 0))

        total.bars_processed += symbol_stats.bars_processed
        total.m15_processed += symbol_stats.m15_processed
        total.m5_processed += symbol_stats.m5_processed
        total.signals_generated += symbol_stats.signals_generated
        total.buy_signals += symbol_stats.buy_signals
        total.sell_signals += symbol_stats.sell_signals
        total.risk_accepted += symbol_stats.risk_accepted
        total.risk_rejected += symbol_stats.risk_rejected
        total.paper_orders += symbol_stats.paper_orders
        total.paper_buy_orders += symbol_stats.paper_buy_orders
        total.paper_sell_orders += symbol_stats.paper_sell_orders
        total.trades_logged += symbol_stats.trades_logged
        total.position_limit_rejected += symbol_stats.position_limit_rejected
        total.regime_policy_rejected += symbol_stats.regime_policy_rejected
        total.symbol_drawdown_rejected += symbol_stats.symbol_drawdown_rejected
        total.loss_streak_rejected += symbol_stats.loss_streak_rejected
        total.portfolio_guard_rejected += symbol_stats.portfolio_guard_rejected
        total.other_execution_rejected += symbol_stats.other_execution_rejected

        print(
            "SYMBOL_STATS "
            f"symbol={symbol} "
            f"bars_processed={symbol_stats.bars_processed} "
            f"m15_processed={symbol_stats.m15_processed} "
            f"m5_processed={symbol_stats.m5_processed} "
            f"signals_generated={symbol_stats.signals_generated} "
            f"buy_signals={symbol_stats.buy_signals} "
            f"sell_signals={symbol_stats.sell_signals} "
            f"risk_accepted={symbol_stats.risk_accepted} "
            f"risk_rejected={symbol_stats.risk_rejected} "
            f"paper_orders={symbol_stats.paper_orders} "
            f"paper_buy_orders={symbol_stats.paper_buy_orders} "
            f"paper_sell_orders={symbol_stats.paper_sell_orders} "
            f"trades_logged={symbol_stats.trades_logged} "
            f"position_limit_rejected={symbol_stats.position_limit_rejected} "
            f"regime_policy_rejected={symbol_stats.regime_policy_rejected} "
            f"symbol_drawdown_rejected={symbol_stats.symbol_drawdown_rejected} "
            f"loss_streak_rejected={symbol_stats.loss_streak_rejected} "
            f"portfolio_guard_rejected={symbol_stats.portfolio_guard_rejected} "
            f"other_execution_rejected={symbol_stats.other_execution_rejected} "
            f"open_position={round(getattr(pipeline, '_br_replay_positions', {}).get(symbol, 0.0), 6)} "
            f"max_abs_position={getattr(pipeline, '_max_abs_position_for_br')(symbol) if hasattr(pipeline, '_max_abs_position_for_br') else 'n/a'} "
            f"limit_source={getattr(getattr(pipeline, 'finam_limits_adapter', None), 'get_symbol_limit')(symbol).source if hasattr(getattr(pipeline, 'finam_limits_adapter', None), 'get_symbol_limit') else 'n/a'} "
            f"finam_current_position={getattr(getattr(pipeline, 'finam_limits_adapter', None), 'get_symbol_limit')(symbol).current_position if hasattr(getattr(pipeline, 'finam_limits_adapter', None), 'get_symbol_limit') else 'n/a'}"
        )

    print("TOTAL_STATS")
    print(f"bars_processed={total.bars_processed}")
    print(f"m15_processed={total.m15_processed}")
    print(f"m5_processed={total.m5_processed}")
    print(f"signals_generated={total.signals_generated}")
    print(f"buy_signals={total.buy_signals}")
    print(f"sell_signals={total.sell_signals}")
    print(f"risk_accepted={total.risk_accepted}")
    print(f"risk_rejected={total.risk_rejected}")
    print(f"paper_orders={total.paper_orders}")
    print(f"paper_buy_orders={total.paper_buy_orders}")
    print(f"paper_sell_orders={total.paper_sell_orders}")
    print(f"trades_logged={total.trades_logged}")
    print(f"position_limit_rejected={total.position_limit_rejected}")
    print(f"regime_policy_rejected={total.regime_policy_rejected}")
    print(f"symbol_drawdown_rejected={total.symbol_drawdown_rejected}")
    print(f"loss_streak_rejected={total.loss_streak_rejected}")
    print(f"portfolio_guard_rejected={total.portfolio_guard_rejected}")
    print(f"other_execution_rejected={total.other_execution_rejected}")
    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())