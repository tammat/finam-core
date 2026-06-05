from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import psycopg2


DDL = """
create table if not exists research_feature_store (
    symbol text not null,
    timeframe text not null,
    ts timestamptz not null,
    close numeric not null,
    atr_14 numeric,
    atr_pct_14 numeric,
    ema_20 numeric,
    ema_50 numeric,
    ema_200 numeric,
    momentum_5 numeric,
    momentum_20 numeric,
    range_pct numeric,
    compression_flag boolean not null default false,
    expansion_flag boolean not null default false,
    source text not null default 'research_feature_store_v1',
    created_at timestamptz not null default now(),
    primary key(symbol, timeframe, ts)
);

create index if not exists idx_research_feature_store_symbol_tf_ts
on research_feature_store(symbol, timeframe, ts desc);
"""


@dataclass(frozen=True, slots=True)
class FeatureBuildResult:
    symbol: str
    timeframe: str
    bars_seen: int
    rows_written: int


class ResearchFeatureStoreBuilder:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def ensure_schema(self) -> None:
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)

    def rebuild_symbol_timeframe(self, symbol: str, timeframe: str, limit: int = 5000) -> FeatureBuildResult:
        self.ensure_schema()

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select ts, open::float8, high::float8, low::float8, close::float8, volume::float8, source
                    from market_bars
                    where symbol=%s and timeframe=%s
                    order by ts desc
                    limit %s
                    """,
                    (symbol, timeframe, limit),
                )
                raw_rows = cur.fetchall()

        rows = list(reversed(raw_rows))
        if not rows:
            return FeatureBuildResult(symbol, timeframe, 0, 0)

        closes = []
        trs = []
        ema20 = None
        ema50 = None
        ema200 = None
        payload = []

        def ema(prev, value, period):
            alpha = 2.0 / (period + 1.0)
            return value if prev is None else value * alpha + prev * (1.0 - alpha)

        for i, row in enumerate(rows):
            ts, open_, high, low, close, volume, bar_source = row
            closes.append(close)

            prev_close = closes[i - 1] if i > 0 else close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)

            atr_14 = sum(trs[-14:]) / 14 if len(trs) >= 14 else None
            atr_pct_14 = atr_14 / close if atr_14 is not None and close else None

            ema20 = ema(ema20, close, 20)
            ema50 = ema(ema50, close, 50)
            ema200 = ema(ema200, close, 200)

            momentum_5 = close - closes[-6] if len(closes) >= 6 else None
            momentum_20 = close - closes[-21] if len(closes) >= 21 else None
            range_pct = (high - low) / close if close else None

            compression_flag = bool(
                atr_pct_14 is not None and range_pct is not None
                and atr_pct_14 < 0.0025 and range_pct < 0.0025
            )
            expansion_flag = bool(
                atr_pct_14 is not None and range_pct is not None
                and range_pct > atr_pct_14 * 1.8
            )

            payload.append((
                symbol, timeframe, ts, close,
                atr_14, atr_pct_14, ema20, ema50, ema200,
                momentum_5, momentum_20, range_pct,
                compression_flag, expansion_flag,
                f"research_feature_store_v1:{bar_source}",
            ))

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    insert into research_feature_store (
                        symbol, timeframe, ts, close,
                        atr_14, atr_pct_14, ema_20, ema_50, ema_200,
                        momentum_5, momentum_20, range_pct,
                        compression_flag, expansion_flag, source
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict (symbol, timeframe, ts)
                    do update set
                        close=excluded.close,
                        atr_14=excluded.atr_14,
                        atr_pct_14=excluded.atr_pct_14,
                        ema_20=excluded.ema_20,
                        ema_50=excluded.ema_50,
                        ema_200=excluded.ema_200,
                        momentum_5=excluded.momentum_5,
                        momentum_20=excluded.momentum_20,
                        range_pct=excluded.range_pct,
                        compression_flag=excluded.compression_flag,
                        expansion_flag=excluded.expansion_flag,
                        source=excluded.source
                    """,
                    payload,
                )

        return FeatureBuildResult(symbol, timeframe, len(rows), len(payload))
