from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_global_edge_ranking_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    trades_count BIGINT NOT NULL DEFAULT 0,
                    net_pnl NUMERIC NOT NULL DEFAULT 0,
                    expectancy NUMERIC NOT NULL DEFAULT 0,
                    profit_factor NUMERIC NOT NULL DEFAULT 0,
                    edge_score NUMERIC NOT NULL DEFAULT 0,
                    rank_no BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(symbol, timeframe, strategy_name)
                );
                """
            )


def _score(trades: int, expectancy: Decimal, profit_factor: Decimal) -> Decimal:
    if trades < 20:
        return Decimal("0")
    if profit_factor <= 1:
        return Decimal("0")
    return expectancy * Decimal("100") + profit_factor * Decimal("10") + Decimal(trades) / Decimal("100")


def rank_edges() -> int:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_name,
                    trades_count,
                    net_pnl,
                    expectancy,
                    profit_factor
                FROM analytics_global_edge_replay_v2
                ORDER BY symbol;
                """
            )
            rows = cur.fetchall()

            scored = []
            for r in rows:
                trades = int(r[4] or 0)
                expectancy = Decimal(str(r[6] or 0))
                pf = Decimal(str(r[7] or 0))
                edge_score = _score(trades, expectancy, pf)

                if edge_score > 0:
                    status = "CANDIDATE"
                elif trades == 0:
                    status = "NO_DATA"
                else:
                    status = "REJECTED"

                scored.append((*r, edge_score, status))

            scored.sort(key=lambda x: x[8], reverse=True)

            saved = 0
            for rank_no, row in enumerate(scored, start=1):
                (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_name,
                    trades_count,
                    net_pnl,
                    expectancy,
                    profit_factor,
                    edge_score,
                    status,
                ) = row

                cur.execute(
                    """
                    INSERT INTO analytics_global_edge_ranking_v2
                        (
                            symbol,
                            asset_class,
                            timeframe,
                            strategy_name,
                            trades_count,
                            net_pnl,
                            expectancy,
                            profit_factor,
                            edge_score,
                            rank_no,
                            status
                        )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (symbol, timeframe, strategy_name)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        trades_count = EXCLUDED.trades_count,
                        net_pnl = EXCLUDED.net_pnl,
                        expectancy = EXCLUDED.expectancy,
                        profit_factor = EXCLUDED.profit_factor,
                        edge_score = EXCLUDED.edge_score,
                        rank_no = EXCLUDED.rank_no,
                        status = EXCLUDED.status;
                    """,
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_name,
                        trades_count,
                        net_pnl,
                        expectancy,
                        profit_factor,
                        edge_score,
                        rank_no,
                        status,
                    ),
                )
                saved += 1

            return saved


def main() -> None:
    saved = rank_edges()

    print("=== EDGE_RANKING_V2 ===")
    print("mode=research_only")
    print(f"ranking_rows={saved}")
    print("candidate_status=CANDIDATE")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("next=FORENSIC_ANALYSIS_V2")
    print("VERDICT=EDGE_RANKING_V2_READY")


if __name__ == "__main__":
    main()
