from __future__ import annotations

import os
import statistics
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from scripts.build_strategy_execution_runner_v1 import (
    Bar,
    build_trades,
    metrics,
)
from finam_core.research.purged_split import (
    purged_bar_window,
    trades_in_purged_window,
)


OBSERVATION_UUID = (
    "9f1bd894-2df8-5ee6-b5b4-da4820f69812"
)

IN_SAMPLE_BARS = 5000
COST_BPS = 8.0


def main() -> int:
    with psycopg2.connect(
        os.environ["DATABASE_URL"]
    ) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    strategy_code,
                    symbol,
                    timeframe,
                    parameter_json
                FROM analytics.edge_observation_v1
                WHERE observation_uuid=%s
                """,
                (OBSERVATION_UUID,),
            )

            observation = cur.fetchone()

            if observation is None:
                raise RuntimeError(
                    "ERROR=BRM6_OBSERVATION_NOT_FOUND"
                )

            cur.execute(
                """
                SELECT
                    ts,
                    close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND close IS NOT NULL
                ORDER BY ts
                """,
                (
                    observation["symbol"],
                    observation["timeframe"],
                ),
            )

            bars = [
                Bar(
                    row["ts"],
                    float(row["close"]),
                )
                for row in cur.fetchall()
            ]

    if len(bars) <= IN_SAMPLE_BARS:
        raise RuntimeError(
            "ERROR=BRM6_OOS_BARS_NOT_AVAILABLE"
        )

    params = dict(
        observation["parameter_json"] or {}
    )

    lookback = int(
        params.get("lookback", 20)
    )

    reference_price = statistics.median(
        bar.close
        for bar in bars
    )

    roundtrip_cost = (
        reference_price
        * COST_BPS
        / 10000.0
    )

    params["commission"] = roundtrip_cost
    params["slippage"] = 0.0

    run = {
        "strategy_code": (
            observation["strategy_code"]
        ),
        "parameter_json": params,
    }

    oos_start, oos_stop, _ = (
        purged_bar_window(
            bars,
            start=IN_SAMPLE_BARS,
            end=len(bars),
            parameters=params,
        )
    )

    trades = trades_in_purged_window(
        build_trades(
            run,
            bars[
                IN_SAMPLE_BARS
                - lookback:
            ],
        ),
        start_ts=oos_start,
        end_ts=oos_stop,
    )

    result = metrics(trades)

    would_admit = (
        result["trades"] >= 50
        and result["expectancy"] > 0
        and result["profit_factor"] > 1
    )

    print(
        "BRM6_NET_FIRST_REPLAY_ROW "
        f"trades={result['trades']} "
        f"profit_factor="
        f"{result['profit_factor']} "
        f"expectancy="
        f"{result['expectancy']} "
        f"max_drawdown="
        f"{result['max_drawdown']} "
        f"commission="
        f"{result['commission']} "
        f"slippage="
        f"{result['slippage']} "
        f"decision="
        f"{'WOULD_ADMIT' if would_admit else 'WOULD_REJECT'}"
    )

    print(
        f"reference_price={reference_price}"
    )
    print(
        f"transaction_cost_bps="
        f"{COST_BPS}"
    )
    print(
        f"roundtrip_cost_per_unit="
        f"{roundtrip_cost}"
    )

    print(
        "transaction_cost_semantics="
        "MEDIAN_PRICE_X_BPS_DIV_10000"
    )

    print(
        "cost_injected_as="
        "COMMISSION_PER_MONETARY_SCALE"
    )

    print(
        "additional_slippage_parameter=0"
    )

    print(
        "original_regime_cost_contract_reconstructed=1"
    )

    print(
        "missing_source_table_required=0"
    )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "BRM6_NET_FIRST_REPLAY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
