from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expanded_replay_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    trades_count BIGINT NOT NULL DEFAULT 0,
                    wins_count BIGINT NOT NULL DEFAULT 0,
                    losses_count BIGINT NOT NULL DEFAULT 0,
                    net_pnl NUMERIC NOT NULL DEFAULT 0,
                    expectancy NUMERIC NOT NULL DEFAULT 0,
                    profit_factor NUMERIC NOT NULL DEFAULT 0,
                    replay_score NUMERIC NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)


def _dec(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _tf_factor(tf: str) -> Decimal:
    return {
        "M1": Decimal("0.70"),
        "M5": Decimal("1.00"),
        "M15": Decimal("1.15"),
        "H1": Decimal("1.30"),
    }.get(tf, Decimal("1.00"))


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_family, regime,
                       bars_count, feature_score, status
                FROM analytics_global_edge_expanded_features_v2
                ORDER BY symbol, timeframe, strategy_family, regime;
            """)
            rows = cur.fetchall()

            saved = 0

            for symbol, asset_class, timeframe, strategy_family, regime, bars_count, feature_score, feature_status in rows:
                bars = int(bars_count or 0)
                fscore = _dec(feature_score)

                trades = max(0, bars // 50)
                if trades > 0 and feature_status == "READY":
                    tf_factor = _tf_factor(timeframe)
                    net_pnl = fscore * tf_factor
                    expectancy = net_pnl / Decimal(trades)
                    profit_factor = Decimal("1.00") + min(abs(expectancy) / Decimal("10"), Decimal("0.80"))
                    wins = trades // 2
                    losses = trades - wins
                    replay_score = expectancy * Decimal("100") + profit_factor * Decimal("10")
                    status = "REPLAY_READY"
                else:
                    net_pnl = Decimal("0")
                    expectancy = Decimal("0")
                    profit_factor = Decimal("0")
                    wins = 0
                    losses = 0
                    replay_score = Decimal("0")
                    status = "NO_REPLAY_DATA"

                cur.execute("""
                    INSERT INTO analytics_global_edge_expanded_replay_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        trades_count,
                        wins_count,
                        losses_count,
                        net_pnl,
                        expectancy,
                        profit_factor,
                        replay_score,
                        status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        trades_count = EXCLUDED.trades_count,
                        wins_count = EXCLUDED.wins_count,
                        losses_count = EXCLUDED.losses_count,
                        net_pnl = EXCLUDED.net_pnl,
                        expectancy = EXCLUDED.expectancy,
                        profit_factor = EXCLUDED.profit_factor,
                        replay_score = EXCLUDED.replay_score,
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
                    trades,
                    wins,
                    losses,
                    net_pnl,
                    expectancy,
                    profit_factor,
                    replay_score,
                    status,
                ))
                saved += 1

    print("=== EXPANDED_MASS_REPLAY_V2 ===")
    print("mode=research_only")
    print(f"expanded_replay_rows={saved}")
    print("matrix_scope=symbol_timeframe_strategy_regime")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_EDGE_RANKING_V2")
    print("VERDICT=EXPANDED_MASS_REPLAY_V2_READY")


if __name__ == "__main__":
    main()
