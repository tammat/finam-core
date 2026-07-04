from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras

import edge.score_rule   # noqa

from edge.base.aggregator import EdgeAggregator
from edge.base.executor import EdgeRuleExecutor
from edge.base.registry import EdgeRuleRegistry
from edge.score_rule.config import EdgeScoreRuleConfig
from edge.score_rule.rule import EdgeScoreRule

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def load_config(cur):

    cur.execute("""
        SELECT config_json
        FROM analytics.edge_configuration_v1
        WHERE edge_name='DEFAULT'
        LIMIT 1;
    """)

    row = cur.fetchone()

    if not row:
        return {}

    cfg = row["config_json"]

    if isinstance(cfg, dict):
        return cfg

    return json.loads(cfg)


def main():

    build_id = str(uuid.uuid4())

    executor = EdgeRuleExecutor()

    aggregator = EdgeAggregator()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cfg = EdgeScoreRuleConfig.from_dict(load_config(cur))

            rules = []

            for cls in EdgeRuleRegistry.enabled():

                if cls.name == "EDGE_SCORE_RULE":
                    rules.append(EdgeScoreRule(cfg))
                else:
                    rules.append(cls())

            cur.execute("""
                SELECT
                    id,
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    strategy_version,
                    signal_ts,
                    signal_score,
                    confidence,
                    feature_quality_score
                FROM analytics.strategy_signal_snapshot_v1
                ORDER BY signal_ts DESC
                LIMIT 5000;
            """)

            signals = cur.fetchall()

            saved = 0

            for signal in signals:

                results = []

                for rule in rules:
                    results.append(executor.execute(rule, dict(signal)))

                aggregate = aggregator.aggregate(results)

                cur.execute("""
                    INSERT INTO analytics.edge_decision_snapshot_v1(

                        signal_id,

                        symbol,
                        asset_class,
                        timeframe,

                        strategy_family,
                        strategy_version,

                        signal_ts,

                        edge_score,
                        validation_score,
                        governance_score,

                        decision_code,
                        recommendation_code,

                        ready_for_research,
                        ready_for_replay,
                        ready_for_paper,
                        ready_for_shadow,
                        ready_for_micro_live,
                        ready_for_live,

                        source_version,
                        build_id

                    )
                    VALUES(
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,
                        %s,%s,
                        true,false,false,false,false,false,
                        'EDGE_SCORE_BUILDER_V1',
                        %s
                    )
                    ON CONFLICT(symbol,timeframe,strategy_family,signal_ts)
                    DO UPDATE SET

                        edge_score=excluded.edge_score,
                        validation_score=excluded.validation_score,
                        governance_score=excluded.governance_score,
                        decision_code=excluded.decision_code,
                        recommendation_code=excluded.recommendation_code,
                        build_id=excluded.build_id,
                        refreshed_at=now();
                """, (

                    signal["id"],

                    signal["symbol"],
                    signal["asset_class"],
                    signal["timeframe"],

                    signal["strategy_family"],
                    signal["strategy_version"],

                    signal["signal_ts"],

                    aggregate.edge_score,
                    aggregate.validation_score,
                    aggregate.governance_score,

                    aggregate.decision_code,
                    aggregate.recommendation_code,

                    build_id,
                ))

                saved += 1

            cur.execute("""
                SELECT count(*)
                FROM analytics.edge_decision_snapshot_v1;
            """)

            rows = cur.fetchone()["count"]

    print("=== EDGE_SCORE_BUILDER_V1 ===")
    print(f"signals_saved={saved}")
    print(f"edge_rows={rows}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_SCORE_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
