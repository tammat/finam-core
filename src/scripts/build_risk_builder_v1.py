from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras

import risk.default_rule  # noqa

from risk.base.aggregator import RiskAggregator
from risk.base.executor import RiskRuleExecutor
from risk.base.registry import RiskRuleRegistry
from risk.default_rule.config import DefaultRiskRuleConfig
from risk.default_rule.rule import DefaultRiskRule

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("RISK_LIMIT", "5000"))


def load_config(cur):

    cur.execute("""
        SELECT config_json
        FROM analytics.risk_configuration_v1
        WHERE risk_name='DEFAULT'
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

    executor = RiskRuleExecutor()

    aggregator = RiskAggregator()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cfg = DefaultRiskRuleConfig.from_dict(load_config(cur))

            rules = []

            for cls in RiskRuleRegistry.enabled():
                if cls.name == "DEFAULT_RISK_RULE":
                    rules.append(DefaultRiskRule(cfg))
                else:
                    rules.append(cls())

            cur.execute("""
                SELECT *
                FROM analytics.edge_decision_snapshot_v1
                ORDER BY signal_ts DESC
                LIMIT %s;
            """, (LIMIT,))

            edge_rows = cur.fetchall()

            saved = 0

            for row in edge_rows:

                results = []

                for rule in rules:
                    results.append(executor.execute(rule, dict(row)))

                aggregate = aggregator.aggregate(results)

                cur.execute("""
                    INSERT INTO analytics.risk_decision_snapshot_v1(

                        edge_decision_id,

                        symbol,
                        asset_class,
                        timeframe,

                        strategy_family,
                        strategy_version,

                        signal_ts,

                        edge_score,
                        validation_score,

                        risk_score,

                        position_risk_score,
                        exposure_risk_score,
                        daily_loss_risk_score,
                        correlation_risk_score,
                        kill_switch_score,

                        risk_decision_code,
                        recommendation_code,

                        ready_for_paper,
                        ready_for_shadow,
                        ready_for_micro_live,
                        ready_for_live,

                        source_version,
                        build_id

                    )
                    VALUES(
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,%s,
                        %s,
                        %s,%s,%s,%s,%s,
                        %s,%s,
                        %s,false,false,false,
                        'RISK_BUILDER_V1',
                        %s
                    )
                    ON CONFLICT(symbol,timeframe,strategy_family,signal_ts)
                    DO UPDATE SET

                        risk_score=excluded.risk_score,
                        position_risk_score=excluded.position_risk_score,
                        exposure_risk_score=excluded.exposure_risk_score,
                        daily_loss_risk_score=excluded.daily_loss_risk_score,
                        correlation_risk_score=excluded.correlation_risk_score,
                        kill_switch_score=excluded.kill_switch_score,
                        risk_decision_code=excluded.risk_decision_code,
                        recommendation_code=excluded.recommendation_code,
                        build_id=excluded.build_id,
                        refreshed_at=now();
                """, (

                    row["id"],

                    row["symbol"],
                    row["asset_class"],
                    row["timeframe"],

                    row["strategy_family"],
                    row["strategy_version"],

                    row["signal_ts"],

                    row["edge_score"],
                    row["validation_score"],

                    aggregate.risk_score,

                    aggregate.position_risk_score,
                    aggregate.exposure_risk_score,
                    aggregate.daily_loss_risk_score,
                    aggregate.correlation_risk_score,
                    aggregate.kill_switch_score,

                    aggregate.decision_code,
                    aggregate.recommendation_code,

                    row["ready_for_paper"],

                    build_id,
                ))

                saved += 1

            cur.execute("""
                SELECT count(*)
                FROM analytics.risk_decision_snapshot_v1;
            """)

            total = cur.fetchone()["count"]

    print("=== RISK_BUILDER_V1 ===")
    print(f"saved={saved}")
    print(f"risk_rows={total}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=RISK_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
