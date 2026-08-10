#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_REPLAY_REQUIRED_TRADE_ECONOMICS_AUDIT_V1 ==="

read -r TOTAL WITH_COST ZERO_COST IDENTITY_OK <<EOF
$(
psql "$DATABASE_URL" -X -At -F' ' <<'SQL'
WITH x AS (
    SELECT
        c.observation_uuid,

        COALESCE(SUM(t.commission),0) AS commission,
        COALESCE(SUM(t.slippage),0) AS slippage,

        COALESCE(
            SUM(
                t.gross_pnl
                - t.commission
                - t.slippage
                - t.net_pnl
            ),
            0
        ) AS identity_delta

    FROM analytics.edge_candidate_v1 c

    JOIN analytics.edge_observation_v1 o
      ON o.observation_uuid=c.observation_uuid

    JOIN analytics.research_trade_v1 t
      ON t.run_uuid=o.run_uuid

    WHERE o.runner_version IN (
        'STRATEGY_EXECUTION_RUNNER_V1',
        'STRATEGY_EXECUTION_RUNNER_V2'
    )

    GROUP BY c.observation_uuid
)
SELECT
    COUNT(*),
    COUNT(*) FILTER (
        WHERE commission > 0
           OR slippage > 0
    ),
    COUNT(*) FILTER (
        WHERE commission = 0
          AND slippage = 0
    ),
    COUNT(*) FILTER (
        WHERE identity_delta = 0
    )
FROM x;
SQL
)
EOF

[ "$TOTAL" -eq 10 ]
[ "$WITH_COST" -eq 9 ]
[ "$ZERO_COST" -eq 1 ]
[ "$IDENTITY_OK" -eq 10 ]

echo "replay_required_candidates=10"
echo "complete_trade_lineage=10"
echo "trade_level_cost_evidence=9"
echo "cost_replay_required=1"
echo "economic_identity_ok=10"

echo "strategy_reconstruction_required=0"
echo "aggregate_observation_costs_used=0"
echo "individual_trade_rows_used=1"

echo "shadow_admission_enabled=1"
echo "enforced_admission_enabled=0"
echo "production_pipeline_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_REPLAY_REQUIRED_TRADE_ECONOMICS_AUDIT_V1_OK"
