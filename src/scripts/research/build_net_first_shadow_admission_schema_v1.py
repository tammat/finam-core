from __future__ import annotations

import os

import psycopg2


DDL = """
CREATE TABLE IF NOT EXISTS analytics.net_first_shadow_admission_v1 (
    id bigserial PRIMARY KEY,

    observation_uuid uuid NOT NULL,

    observed_at timestamptz NOT NULL DEFAULT now(),

    candidate_code text NOT NULL,
    symbol text NOT NULL,
    strategy_code text NOT NULL,
    timeframe text NOT NULL,

    canonical_trades integer NOT NULL,

    gross_pnl numeric NOT NULL,
    total_cost numeric NOT NULL,
    net_pnl numeric NOT NULL,
    net_expectancy numeric NOT NULL,
    net_profit_factor numeric NOT NULL,

    economic_gate_status text NOT NULL,

    shadow_decision text NOT NULL
        CHECK (
            shadow_decision IN (
                'WOULD_REJECT',
                'WOULD_ADMIT'
            )
        ),

    actual_robustness_scheduled boolean,

    production_blocked boolean NOT NULL DEFAULT false,

    cost_contract_version text NOT NULL,
    policy_version text NOT NULL,
    source_version text NOT NULL,

    UNIQUE (
        observation_uuid
    )
);

CREATE INDEX IF NOT EXISTS
    net_first_shadow_admission_candidate_idx
ON analytics.net_first_shadow_admission_v1 (
    strategy_code,
    symbol,
    timeframe,
    observed_at DESC
);

CREATE INDEX IF NOT EXISTS
    net_first_shadow_admission_decision_idx
ON analytics.net_first_shadow_admission_v1 (
    shadow_decision,
    observed_at DESC
);
"""


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit(
            "ERROR=DATABASE_URL_NOT_SET"
        )

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)

        conn.commit()

    print(
        "table="
        "analytics.net_first_shadow_admission_v1"
    )

    print("shadow_admission_enabled=1")
    print("enforced_admission_enabled=0")
    print("production_pipeline_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "NET_FIRST_SHADOW_ADMISSION_SCHEMA_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
