from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor


SYMBOL = "USDRUBF@RTSX"
EXCHANGE = "RTSX"
ASSET_CLASS = "FUTURES"

EXPECTED_SOURCE = "TRADING_COST_MODEL_NORMALIZATION_V1"

TICK_SIZE = Decimal("0.01")
TICK_VALUE_RUB = Decimal("10")


def dec(value) -> Decimal:
    return Decimal(str(value))


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit("ERROR=DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    slippage_profile_code,
                    slippage_per_trade,
                    source_version,
                    is_active
                FROM analytics.slippage_profile_v1
                WHERE exchange_code=%s
                  AND asset_class=%s
                  AND is_active=true
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (EXCHANGE, ASSET_CLASS),
            )

            row = cur.fetchone()

    if not row:
        raise RuntimeError(
            "ERROR=RTSX_FUTURES_SLIPPAGE_PROFILE_MISSING"
        )

    slippage_per_side_rub = dec(
        row["slippage_per_trade"]
    )

    if slippage_per_side_rub < 0:
        raise RuntimeError(
            "ERROR=NEGATIVE_SLIPPAGE_PROFILE"
        )

    round_trip_slippage_rub = (
        slippage_per_side_rub * Decimal("2")
    )

    slippage_ticks_per_side = (
        slippage_per_side_rub
        / TICK_VALUE_RUB
    )

    one_tick_per_side_rub = TICK_VALUE_RUB

    one_tick_round_trip_rub = (
        one_tick_per_side_rub
        * Decimal("2")
    )

    source_version = str(
        row["source_version"]
    )

    actual_slippage_evidence = False

    print(
        "SLIPPAGE_PROFILE_ROW "
        f"symbol={SYMBOL} "
        f"profile={row['slippage_profile_code']} "
        f"slippage_per_side_rub="
        f"{slippage_per_side_rub} "
        f"round_trip_slippage_rub="
        f"{round_trip_slippage_rub} "
        f"source_version={source_version}"
    )

    print(
        "SLIPPAGE_SCALE_ROW "
        f"tick_size={TICK_SIZE} "
        f"tick_value_rub={TICK_VALUE_RUB} "
        f"registry_slippage_ticks_per_side="
        f"{slippage_ticks_per_side}"
    )

    print(
        "BASELINE_SCENARIO "
        "code=REGISTRY_BASELINE "
        f"slippage_per_side_rub="
        f"{slippage_per_side_rub} "
        f"round_trip_slippage_rub="
        f"{round_trip_slippage_rub}"
    )

    print(
        "STRESS_SCENARIO "
        "code=ONE_TICK_STRESS "
        f"slippage_per_side_rub="
        f"{one_tick_per_side_rub} "
        f"round_trip_slippage_rub="
        f"{one_tick_round_trip_rub}"
    )

    print(
        "slippage_application_semantics="
        "FIXED_MONETARY_PER_SIDE"
    )

    print("slippage_currency=RUB")

    print(
        f"actual_slippage_evidence="
        f"{int(actual_slippage_evidence)}"
    )

    print(
        "registry_source_is_actual_execution_evidence=0"
    )

    print(
        "registry_source_is_normalized_fallback="
        f"{int(source_version == EXPECTED_SOURCE)}"
    )

    print("funding_separate=1")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "USDRUBF_FUTURES_SLIPPAGE_SEMANTICS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
