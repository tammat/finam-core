from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg2


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    timeframe: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketBarsSource:
    """Русский комментарий: единый persistent source исторических баров."""

    def __init__(self, dsn: str):
        self.dsn = dsn

    def ensure_schema(self) -> None:
        conn = psycopg2.connect(self.dsn)

        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        create table if not exists market_bars (
                            symbol text not null,
                            timeframe text not null,
                            ts timestamptz not null,

                            open numeric not null,
                            high numeric not null,
                            low numeric not null,
                            close numeric not null,
                            volume numeric not null default 0,

                            created_at timestamptz not null default now(),

                            primary key(symbol, timeframe, ts)
                        )
                    """)

                    cur.execute("""
                        create index if not exists idx_market_bars_symbol_tf_ts
                        on market_bars(symbol, timeframe, ts desc)
                    """)
        finally:
            conn.close()

    def insert_bar(self, bar: MarketBar) -> None:
        conn = psycopg2.connect(self.dsn)

        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        insert into market_bars (
                            symbol,
                            timeframe,
                            ts,
                            open,
                            high,
                            low,
                            close,
                            volume
                        )
                        values (%s,%s,%s,%s,%s,%s,%s,%s)
                        on conflict (symbol, timeframe, ts)
                        do update set
                            open=excluded.open,
                            high=excluded.high,
                            low=excluded.low,
                            close=excluded.close,
                            volume=excluded.volume
                    """, (
                        bar.symbol,
                        bar.timeframe,
                        bar.ts,
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume,
                    ))
        finally:
            conn.close()

    def load_closes(
        self,
        *,
        symbol: str,
        timeframe: str = "M5",
        limit: int = 200,
    ) -> list[float]:
        conn = psycopg2.connect(self.dsn)

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    select close
                    from market_bars
                    where symbol=%s
                      and timeframe=%s
                    order by ts desc
                    limit %s
                """, (
                    symbol,
                    timeframe,
                    limit,
                ))

                rows = cur.fetchall()

                return [float(r[0]) for r in reversed(rows)]
        finally:
            conn.close()
