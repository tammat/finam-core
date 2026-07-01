from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expanded_ranking_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    trades_count BIGINT NOT NULL DEFAULT 0,
                    net_pnl NUMERIC NOT NULL DEFAULT 0,
                    expectancy NUMERIC NOT NULL DEFAULT 0,
                    profit_factor NUMERIC NOT NULL DEFAULT 0,
                    replay_score NUMERIC NOT NULL DEFAULT 0,
                    edge_score NUMERIC NOT NULL DEFAULT 0,
                    rank_no BIGINT NOT NULL,
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


def _edge_score(trades: int, expectancy: Decimal, pf: Decimal, replay_score: Decimal) -> Decimal:
    if trades < 20:
        return Decimal("0")
    if expectancy <= 0:
        return Decimal("0")
    if pf <= Decimal("1.05"):
        return Decimal("0")
    return replay_score + Decimal(trades) / Decimal("100")


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    trades_count,
                    net_pnl,
                    expectancy,
                    profit_factor,
                    replay_score
                FROM analytics_global_edge_expanded_replay_v2
                ORDER BY symbol, timeframe, strategy_family, regime;
            """)
            rows = cur.fetchall()

            scored = []
            for row in rows:
                trades = int(row[5] or 0)
                expectancy = _dec(row[7])
                pf = _dec(row[8])
                replay_score = _dec(row[9])
                edge_score = _edge_score(trades, expectancy, pf, replay_score)

                if edge_score > 0:
                    status = "CANDIDATE"
                elif trades == 0:
                    status = "NO_DATA"
                else:
                    status = "REJECTED"

                scored.append((*row, edge_score, status))

            scored.sort(key=lambda x: x[10], reverse=True)

            saved = 0
            for rank_no, row in enumerate(scored, start=1):
                (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    trades_count,
                    net_pnl,
                    expectancy,
                    profit_factor,
                    replay_score,
                    edge_score,
                    status,
                ) = row

                cur.execute("""
                    INSERT INTO analytics_global_edge_expanded_ranking_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        trades_count,
                        net_pnl,
                        expectancy,
                        profit_factor,
                        replay_score,
                        edge_score,
                        rank_no,
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
                        net_pnl = EXCLUDED.net_pnl,
                        expectancy = EXCLUDED.expectancy,
                        profit_factor = EXCLUDED.profit_factor,
                        replay_score = EXCLUDED.replay_score,
                        edge_score = EXCLUDED.edge_score,
                        rank_no = EXCLUDED.rank_no,
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
                    trades_count,
                    net_pnl,
                    expectancy,
                    profit_factor,
                    replay_score,
                    edge_score,
                    rank_no,
                    status,
                ))
                saved += 1

    print("=== EXPANDED_EDGE_RANKING_V2 ===")
    print("mode=research_only")
    print(f"expanded_ranking_rows={saved}")
    print("matrix_scope=symbol_timeframe_strategy_regime")
    print("candidate_status=CANDIDATE")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_FORENSIC_ANALYSIS_V2")
    print("VERDICT=EXPANDED_EDGE_RANKING_V2_READY")


if __name__ == "__main__":
    main()
