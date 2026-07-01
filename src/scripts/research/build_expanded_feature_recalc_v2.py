from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expanded_features_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    bars_count BIGINT NOT NULL DEFAULT 0,
                    last_close NUMERIC,
                    atr_proxy NUMERIC,
                    return_proxy NUMERIC,
                    feature_score NUMERIC NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)


def table_exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None


def score(strategy_family: str, regime: str, bars: int, atr: Decimal, ret: Decimal) -> Decimal:
    if bars <= 0:
        return Decimal("0")

    base = abs(ret) + abs(atr) / Decimal("10")

    if strategy_family == "BREAKOUT" and regime in {"TREND", "HIGH_VOLATILITY", "COMPRESSION"}:
        return base * Decimal("1.20")
    if strategy_family == "MEAN_REVERSION" and regime in {"RANGE", "LOW_VOLATILITY"}:
        return base * Decimal("1.10")
    if strategy_family == "TREND_FOLLOWING" and regime == "TREND":
        return base * Decimal("1.30")
    if strategy_family == "VOLATILITY_EXPANSION" and regime in {"COMPRESSION", "HIGH_VOLATILITY"}:
        return base * Decimal("1.25")

    return base * Decimal("0.75")


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_family, regime
                FROM analytics_global_edge_regime_matrix_v2
                WHERE status='READY'
                ORDER BY symbol, timeframe, strategy_family, regime;
            """)
            rows = cur.fetchall()

            has_bars = table_exists(cur, "public.market_bars")
            saved = 0

            for symbol, asset_class, timeframe, strategy_family, regime in rows:
                bars_count = 0
                last_close = None
                atr_proxy = None
                return_proxy = None
                feature_score = Decimal("0")
                status = "NO_BARS"

                if has_bars:
                    cur.execute("""
                        SELECT
                            count(*),
                            max(close),
                            max(high) - min(low),
                            max(close) - min(close)
                        FROM public.market_bars
                        WHERE symbol = %s
                           OR symbol = split_part(%s, '@', 1);
                    """, (symbol, symbol))
                    row = cur.fetchone()
                    bars_count = int(row[0] or 0)
                    last_close = row[1]
                    atr_proxy = row[2]
                    return_proxy = row[3]

                    atr = Decimal(str(atr_proxy or 0))
                    ret = Decimal(str(return_proxy or 0))
                    feature_score = score(strategy_family, regime, bars_count, atr, ret)
                    status = "READY" if bars_count > 0 else "NO_BARS"

                cur.execute("""
                    INSERT INTO analytics_global_edge_expanded_features_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        bars_count,
                        last_close,
                        atr_proxy,
                        return_proxy,
                        feature_score,
                        status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        bars_count = EXCLUDED.bars_count,
                        last_close = EXCLUDED.last_close,
                        atr_proxy = EXCLUDED.atr_proxy,
                        return_proxy = EXCLUDED.return_proxy,
                        feature_score = EXCLUDED.feature_score,
                        status = EXCLUDED.status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    bars_count,
                    last_close,
                    atr_proxy,
                    return_proxy,
                    feature_score,
                    status,
                ))
                saved += 1

    print("=== EXPANDED_FEATURE_RECALC_V2 ===")
    print("mode=research_only")
    print(f"expanded_feature_rows={saved}")
    print("matrix_scope=symbol_timeframe_strategy_regime")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_MASS_REPLAY_V2")
    print("VERDICT=EXPANDED_FEATURE_RECALC_V2_READY")


if __name__ == "__main__":
    main()
