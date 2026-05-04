"""
Replay исторических BR M5/M15 баров через PAPER signal processor.
Русский комментарий: скрипт не отправляет заявки и не использует broker execution.
Он читает market_data из PostgreSQL и вызывает тот же метод pipeline,
который используется live-режимом для BR PAPER-сигналов.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2

from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
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



class NullNotifier:
    """Русский комментарий: replay не должен спамить Telegram историческими сигналами."""

    def send(self, text: str) -> None:
        return None


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

    def __getattr__(self, name):
        return getattr(self.inner, name)


def dsn() -> str:
    return (
        f"postgresql://{os.getenv('DB_USER', 'finam')}:{os.getenv('DB_PASSWORD', 'finam')}"
        f"@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'finam')}"
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


# Helper: get columns in market_data table
def get_market_data_columns(conn) -> set[str]:
    """Русский комментарий: определяем фактические колонки market_data на текущей БД."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'market_data'
            """
        )
        return {str(row[0]) for row in cur.fetchall()}



def load_bars(symbol: str, from_ts=None, to_ts=None) -> list[ReplayBar]:
    """Русский комментарий: загружаем M15 и M5 бары; если OHLC нет, строим их из close_price."""
    where = ["symbol = %s", "timeframe IN ('M15', 'M5')"]
    params: list[object] = [symbol]

    if from_ts is not None:
        where.append("ts >= %s")
        params.append(from_ts)
    if to_ts is not None:
        where.append("ts <= %s")
        params.append(to_ts)

    rows: list[ReplayBar] = []
    with psycopg2.connect(dsn()) as conn:
        columns = get_market_data_columns(conn)

        close_col = "close_price" if "close_price" in columns else "close"
        open_expr = "open_price" if "open_price" in columns else close_col
        high_expr = "high_price" if "high_price" in columns else close_col
        low_expr = "low_price" if "low_price" in columns else close_col
        volume_expr = "volume" if "volume" in columns else "0.0"

        sql = f"""
            SELECT
                symbol,
                timeframe,
                ts,
                {open_expr} AS open_value,
                {high_expr} AS high_value,
                {low_expr} AS low_value,
                {close_col} AS close_value,
                {volume_expr} AS volume_value
            FROM market_data
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


def build_replay_pipeline(symbol: str):
    """Русский комментарий: создаем минимальный pipeline-объект только для BR signal processor."""
    pipeline = object.__new__(PaperTradingPipeline)
    pipeline.br_breakout_enabled = True
    pipeline.br_breakout_symbol = symbol
    pipeline.br_breakout = BrConservativeBreakout(symbol=symbol)
    base_logger = PostgresLogger()
    pipeline.pg_logger = CountingLogger(base_logger)
    pipeline.notifier = NullNotifier()
    return pipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRM6@RTSX")
    parser.add_argument("--from-ts")
    parser.add_argument("--to-ts")
    args = parser.parse_args()

    os.environ["EXECUTION_MODE"] = os.getenv("EXECUTION_MODE", "paper")
    os.environ["ENABLE_BR_CONSERVATIVE_BREAKOUT"] = "1"
    os.environ["BR_BREAKOUT_SYMBOL"] = args.symbol

    bars = load_bars(
        symbol=args.symbol,
        from_ts=parse_ts(args.from_ts),
        to_ts=parse_ts(args.to_ts),
    )

    pipeline = build_replay_pipeline(args.symbol)

    m15_count = 0
    m5_count = 0

    processed = 0
    for bar in bars:
        tf = str(bar.timeframe).upper()
        if tf == "M15":
            m15_count += 1
        elif tf == "M5":
            m5_count += 1

        pipeline._process_br_closed_bar_for_paper_signal(bar)
        processed += 1

    print("REPLAY_BR_PIPELINE")
    print(f"symbol={args.symbol}")
    print(f"bars_processed={processed}")
    logger = pipeline.pg_logger
    print(f"m15_processed={m15_count}")
    print(f"m5_processed={m5_count}")
    print(f"signals_generated={getattr(logger, 'signals_total', 0)}")
    print(f"buy_signals={getattr(logger, 'buy_count', 0)}")
    print(f"sell_signals={getattr(logger, 'sell_count', 0)}")
    print(f"risk_accepted={getattr(logger, 'risk_accepted_count', 0)}")
    print(f"risk_rejected={getattr(logger, 'risk_rejected_count', 0)}")
    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())