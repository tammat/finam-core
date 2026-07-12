from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "TRIAL_GROSS_NET_ATTRIBUTION_V1"
BPS_FAMILIES = {"RELATIVE_STRENGTH", "INTERMARKET_LEAD_LAG"}


def main() -> None:
    attribution_run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT execution_run_id FROM analytics.strategy_hypothesis_execution_run_v2
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            if not latest:
                raise RuntimeError("NO_EXECUTION_RUN_V2")
            execution_run_id = latest["execution_run_id"]
            cur.execute("""SELECT percentile_cont(0.5) WITHIN GROUP(ORDER BY close) AS median_price
                FROM public.market_bars WHERE symbol='IMOEX' AND timeframe='M5' AND close IS NOT NULL""")
            imoex_median = float(cur.fetchone()["median_price"])
            cur.execute("""SELECT r.*,t.trial_id,t.hypothesis_id
                FROM analytics.strategy_hypothesis_execution_result_v2 r
                JOIN analytics.hypothesis_trial_registry_v2 t
                  ON t.execution_run_id=r.execution_run_id AND t.candidate_hash=r.candidate_hash
                WHERE r.execution_run_id=%s ORDER BY r.candidate_hash""", (execution_run_id,))
            rows = cur.fetchall()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.trial_gross_net_attribution_v1 (
                    attribution_run_id uuid NOT NULL, execution_run_id uuid NOT NULL,
                    trial_id uuid NOT NULL, hypothesis_id uuid NOT NULL,
                    strategy_family text NOT NULL, pnl_unit text NOT NULL,
                    oos_trades integer NOT NULL, transaction_cost_bps numeric NOT NULL,
                    per_trade_cost numeric NOT NULL, net_expectancy numeric NOT NULL,
                    estimated_gross_expectancy numeric NOT NULL,
                    net_profit_factor numeric NOT NULL, gross_profit_factor numeric,
                    attribution_status text NOT NULL, diagnosis_code text NOT NULL,
                    promotion_allowed boolean NOT NULL DEFAULT false,
                    source_version text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(attribution_run_id,trial_id)
                );
                CREATE INDEX IF NOT EXISTS trial_gross_net_attribution_latest_idx
                    ON analytics.trial_gross_net_attribution_v1(created_at DESC,strategy_family,diagnosis_code);
            """)
            counts = {"NO_RAW_EDGE": 0, "EDGE_DESTROYED_BY_COSTS": 0}
            for row in rows:
                family = row["strategy_family"]
                pnl_unit = "BPS" if family in BPS_FAMILIES else "PRICE_POINTS"
                per_trade_cost = 8.0 if pnl_unit == "BPS" else imoex_median * 8.0 / 10000.0
                net = float(row["oos_expectancy"] or 0)
                gross = net + per_trade_cost
                diagnosis = "EDGE_DESTROYED_BY_COSTS" if gross > 0 and net <= 0 else "NO_RAW_EDGE"
                counts[diagnosis] += 1
                cur.execute("""INSERT INTO analytics.trial_gross_net_attribution_v1
                    (attribution_run_id,execution_run_id,trial_id,hypothesis_id,strategy_family,pnl_unit,
                     oos_trades,transaction_cost_bps,per_trade_cost,net_expectancy,estimated_gross_expectancy,
                     net_profit_factor,gross_profit_factor,attribution_status,diagnosis_code,promotion_allowed,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,8,%s,%s,%s,%s,NULL,'PARTIAL_EXPECTANCY_EXACT_PF_UNAVAILABLE',%s,false,%s)""",
                    (attribution_run_id,execution_run_id,row["trial_id"],row["hypothesis_id"],family,pnl_unit,
                     row["oos_trades"],per_trade_cost,net,gross,row["oos_profit_factor"],diagnosis,SOURCE_VERSION))

    print(f"attribution_run_id={attribution_run_id}")
    print(f"execution_run_id={execution_run_id}")
    print(f"attributed_trials={len(rows)}")
    print(f"no_raw_edge={counts['NO_RAW_EDGE']}")
    print(f"edge_destroyed_by_costs={counts['EDGE_DESTROYED_BY_COSTS']}")
    print("gross_profit_factor_status=UNAVAILABLE_REQUIRES_TRADE_LEVEL_REPLAY")
    print("verdicts_changed=0")
    print("paper_created=0")
    print("live_allowed=0")
    print("VERDICT=TRIAL_GROSS_NET_ATTRIBUTION_V1_OK")


if __name__ == "__main__":
    main()
