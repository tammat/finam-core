from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def main() -> int:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runtime_capital_allocator (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    runtime_state TEXT NOT NULL,
                    edge_score NUMERIC NOT NULL,
                    profit_factor NUMERIC NOT NULL,
                    expectancy NUMERIC NOT NULL,
                    winrate NUMERIC NOT NULL,
                    radar_rank INTEGER NOT NULL,
                    allocation_score NUMERIC NOT NULL,
                    capital_weight NUMERIC NOT NULL,
                    risk_multiplier NUMERIC NOT NULL,
                    allocator_decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe)
                );

                CREATE INDEX IF NOT EXISTS idx_runtime_capital_allocator_rank
                ON runtime_capital_allocator(capital_weight DESC);

                CREATE INDEX IF NOT EXISTS idx_runtime_capital_allocator_symbol
                ON runtime_capital_allocator(symbol, strategy, timeframe);
            """)

            cur.execute("""
                SELECT
                    r.symbol,
                    COALESCE(u.strategy, 'UNKNOWN'),
                    COALESCE(u.timeframe, r.timeframe),
                    COALESCE(s.runtime_state, 'DISABLED'),
                    COALESCE(r.edge_score, 0),
                    COALESCE(st.profit_factor, 0),
                    COALESCE(st.expectancy, 0),
                    COALESCE(st.winrate, 0),
                    COALESCE(r.candidate_rank, 999999)
                FROM market_radar_candidates r
                LEFT JOIN runtime_active_universe u
                    ON u.symbol = r.symbol
                LEFT JOIN ng_live_runtime_state s
                    ON s.symbol = u.symbol
                   AND s.strategy = u.strategy
                   AND s.timeframe = u.timeframe
                LEFT JOIN strategy_statistics_v2 st
                    ON st.symbol = u.symbol
                   AND st.strategy = u.strategy
                   AND st.timeframe = u.timeframe
                WHERE r.symbol IS NOT NULL
            """)

            rows = cur.fetchall()

            scored = []

            for row in rows:
                (
                    symbol,
                    strategy,
                    timeframe,
                    runtime_state,
                    edge_score,
                    pf,
                    expectancy,
                    winrate,
                    radar_rank,
                ) = row

                edge_score = safe_float(edge_score)
                pf = safe_float(pf)
                expectancy = safe_float(expectancy)
                winrate = safe_float(winrate)

                pf_score = clamp((pf - 1.0) / 2.0)
                expectancy_score = clamp(expectancy / 0.02)
                winrate_score = clamp(winrate)

                allocation_score = (
                    0.40 * edge_score
                    + 0.30 * pf_score
                    + 0.20 * expectancy_score
                    + 0.10 * winrate_score
                )

                if runtime_state != "ACTIVE":
                    allocation_score *= 0.25

                if strategy == "UNKNOWN":
                    allocation_score = 0.0

                capital_weight = clamp(allocation_score)

                if capital_weight >= 0.75:
                    risk_multiplier = 1.50
                    allocator_decision = "AGGRESSIVE"
                elif capital_weight >= 0.50:
                    risk_multiplier = 1.00
                    allocator_decision = "NORMAL"
                elif capital_weight >= 0.25:
                    risk_multiplier = 0.50
                    allocator_decision = "REDUCED"
                else:
                    risk_multiplier = 0.0
                    allocator_decision = "BLOCK"

                reason = (
                    f"edge={round(edge_score,4)} "
                    f"pf={round(pf,4)} "
                    f"expectancy={round(expectancy,6)} "
                    f"winrate={round(winrate,4)} "
                    f"runtime_state={runtime_state}"
                )

                scored.append((
                    symbol,
                    strategy,
                    timeframe,
                    runtime_state,
                    edge_score,
                    pf,
                    expectancy,
                    winrate,
                    radar_rank,
                    allocation_score,
                    capital_weight,
                    risk_multiplier,
                    allocator_decision,
                    reason,
                ))

            scored.sort(key=lambda x: float(x[10]), reverse=True)

            saved = 0

            for item in scored:
                (
                    symbol,
                    strategy,
                    timeframe,
                    runtime_state,
                    edge_score,
                    pf,
                    expectancy,
                    winrate,
                    radar_rank,
                    allocation_score,
                    capital_weight,
                    risk_multiplier,
                    allocator_decision,
                    reason,
                ) = item

                cur.execute("""
                    INSERT INTO runtime_capital_allocator (
                        symbol,
                        strategy,
                        timeframe,
                        runtime_state,
                        edge_score,
                        profit_factor,
                        expectancy,
                        winrate,
                        radar_rank,
                        allocation_score,
                        capital_weight,
                        risk_multiplier,
                        allocator_decision,
                        reason,
                        calculated_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now()
                    )
                    ON CONFLICT(symbol, strategy, timeframe)
                    DO UPDATE SET
                        runtime_state=EXCLUDED.runtime_state,
                        edge_score=EXCLUDED.edge_score,
                        profit_factor=EXCLUDED.profit_factor,
                        expectancy=EXCLUDED.expectancy,
                        winrate=EXCLUDED.winrate,
                        radar_rank=EXCLUDED.radar_rank,
                        allocation_score=EXCLUDED.allocation_score,
                        capital_weight=EXCLUDED.capital_weight,
                        risk_multiplier=EXCLUDED.risk_multiplier,
                        allocator_decision=EXCLUDED.allocator_decision,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol,
                    strategy,
                    timeframe,
                    runtime_state,
                    edge_score,
                    pf,
                    expectancy,
                    winrate,
                    radar_rank,
                    allocation_score,
                    capital_weight,
                    risk_multiplier,
                    allocator_decision,
                    reason,
                ))

                print(
                    "RUNTIME_CAPITAL_ALLOCATOR "
                    f"symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"allocation={round(capital_weight,4)} "
                    f"risk_multiplier={round(risk_multiplier,2)} "
                    f"decision={allocator_decision} "
                    f"reason={reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"RUNTIME_CAPITAL_ALLOCATOR_SUMMARY saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
