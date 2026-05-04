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


def load_bars(symbol: str, from_ts=None, to_ts=None) -> list[ReplayBar]:
    """Русский комментарий: загружаем M15 и M5 бары; M15 идет первым при равном ts."""
    where = ["symbol = %s", "timeframe IN ('M15', 'M5')"]
    params: list[object] = [symbol]

    if from_ts is not None:
        where.append("ts >= %s")
        params.append(from_ts)
    if to_ts is not None:
        where.append("ts <= %s")
        params.append(to_ts)

    sql = f"""
        SELECT symbol, timeframe, ts, open_price, high_price, low_price, close_price, volume
        FROM market_data
        WHERE {' AND '.join(where)}
        ORDER BY ts ASC,
                 CASE WHEN timeframe = 'M15' THEN 0 WHEN timeframe = 'M5' THEN 1 ELSE 2 END ASC
    """

    rows: list[ReplayBar] = []
    with psycopg2.connect(dsn()) as conn:
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
    pipeline.pg_logger = PostgresLogger()
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

    processed = 0
    for bar in bars:
        pipeline._process_br_closed_bar_for_paper_signal(bar)
        processed += 1

    print("REPLAY_BR_PIPELINE")
    print(f"symbol={args.symbol}")
    print(f"bars_processed={processed}")
    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())