from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    r.rank_no,
                    r.symbol,
                    r.asset_class,
                    r.timeframe,
                    r.strategy_family,
                    r.regime,
                    r.trades_count,
                    r.expectancy,
                    r.profit_factor,
                    r.edge_score,
                    f.forensic_status,
                    rb.robustness_status,
                    rb.degradation_pct,
                    wf.walk_forward_status,
                    wf.train_expectancy,
                    wf.test_expectancy,
                    wf.train_profit_factor,
                    wf.test_profit_factor
                FROM analytics_global_edge_expanded_ranking_v2 r
                JOIN analytics_global_edge_expanded_forensic_v2 f
                  ON f.symbol=r.symbol AND f.timeframe=r.timeframe
                 AND f.strategy_family=r.strategy_family AND f.regime=r.regime
                JOIN analytics_global_edge_expanded_robustness_v2 rb
                  ON rb.symbol=r.symbol AND rb.timeframe=r.timeframe
                 AND rb.strategy_family=r.strategy_family AND rb.regime=r.regime
                JOIN analytics_global_edge_expanded_walk_forward_v2 wf
                  ON wf.symbol=r.symbol AND wf.timeframe=r.timeframe
                 AND wf.strategy_family=r.strategy_family AND wf.regime=r.regime
                WHERE r.status='CANDIDATE'
                ORDER BY r.edge_score DESC, r.trades_count DESC
                LIMIT 3;
            """)
            rows = cur.fetchall()

    top3_candidates = 0
    top3_rejected = 0

    print("=== EXPANDED_EDGE_TOP3_FORENSIC_DEEP_DIVE_V1 ===")
    print("mode=research_only")

    for idx, row in enumerate(rows, start=1):
        (
            rank_no, symbol, asset_class, timeframe, strategy_family, regime,
            trades, expectancy, pf, edge_score,
            forensic_status, robustness_status, degradation_pct,
            walk_forward_status, train_exp, test_exp, train_pf, test_pf,
        ) = row

        final = (
            "TOP3_CANDIDATE"
            if forensic_status == "FORENSIC_PASS"
            and robustness_status == "ROBUST_PASS"
            and walk_forward_status == "WALK_FORWARD_PASS"
            else "TOP3_REJECT"
        )

        if final == "TOP3_CANDIDATE":
            top3_candidates += 1
        else:
            top3_rejected += 1

        print(f"TOP{idx}")
        print(f"rank_no={rank_no}")
        print(f"symbol={symbol}")
        print(f"asset_class={asset_class}")
        print(f"timeframe={timeframe}")
        print(f"strategy_family={strategy_family}")
        print(f"regime={regime}")
        print(f"trades={trades}")
        print(f"expectancy={expectancy}")
        print(f"profit_factor={pf}")
        print(f"edge_score={edge_score}")
        print(f"forensic_status={forensic_status}")
        print(f"robustness_status={robustness_status}")
        print(f"degradation_pct={degradation_pct}")
        print(f"walk_forward_status={walk_forward_status}")
        print(f"train_expectancy={train_exp}")
        print(f"test_expectancy={test_exp}")
        print(f"train_profit_factor={train_pf}")
        print(f"test_profit_factor={test_pf}")
        print(f"FINAL_VERDICT={final}")

    print(f"summary_top3={len(rows)}")
    print(f"top3_candidates={top3_candidates}")
    print(f"top3_rejected={top3_rejected}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_OUT_OF_SAMPLE_VALIDATION_V1")
    print("VERDICT=EXPANDED_EDGE_TOP3_FORENSIC_DEEP_DIVE_V1_READY")


if __name__ == "__main__":
    main()
