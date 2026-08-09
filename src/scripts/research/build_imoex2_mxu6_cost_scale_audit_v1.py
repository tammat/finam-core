#!/usr/bin/env python3
"""
IMOEX2_MXU6_COST_SCALE_AUDIT_V1

Проверяет, допустимо ли переносить execution costs MXU6
в ценовые единицы IMOEX2.

Read-only.
Никаких торговых решений.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


SIGNAL_SYMBOL = "IMOEX2"
EXECUTION_SYMBOL = "MXU6@RTSX"
TIMEFRAME = "M5"


def d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def main() -> int:
    print("=== IMOEX2 MXU6 COST SCALE AUDIT V1 ===")
    print("mode=research_read_only")
    print(f"signal_symbol={SIGNAL_SYMBOL}")
    print(f"execution_symbol={EXECUTION_SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    percentile_cont(0.5)
                        WITHIN GROUP (ORDER BY close::numeric)
                        AS median_close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND close>0
                """,
                (SIGNAL_SYMBOL, TIMEFRAME),
            )
            signal = dict(cur.fetchone() or {})

            cur.execute(
                """
                SELECT
                    percentile_cont(0.5)
                        WITHIN GROUP (ORDER BY close::numeric)
                        AS median_close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND close>0
                """,
                (EXECUTION_SYMBOL, TIMEFRAME),
            )
            execution = dict(cur.fetchone() or {})

            cur.execute(
                """
                SELECT
                    tick_size,
                    tick_value
                FROM analytics.market_contract_spec_v1
                WHERE symbol=%s
                  AND is_active=true
                ORDER BY valid_from DESC
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )
            contract = dict(cur.fetchone() or {})

            cur.execute(
                """
                SELECT
                    buy_sell_fee
                FROM analytics.market_contract_cost_spec_v1
                WHERE symbol=%s
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )
            cost = dict(cur.fetchone() or {})

            # Совпадающие timestamp'ы и корреляция доходностей.
            cur.execute(
                """
                WITH joined AS (
                    SELECT
                        s.ts,
                        s.close::numeric AS signal_close,
                        e.close::numeric AS execution_close
                    FROM public.market_bars s
                    JOIN public.market_bars e
                      ON e.ts=s.ts
                     AND e.timeframe=s.timeframe
                    WHERE s.symbol=%s
                      AND e.symbol=%s
                      AND s.timeframe=%s
                      AND s.close>0
                      AND e.close>0
                ),
                ret AS (
                    SELECT
                        ts,
                        signal_close,
                        execution_close,

                        signal_close
                        / lag(signal_close) OVER (ORDER BY ts)
                        - 1 AS signal_return,

                        execution_close
                        / lag(execution_close) OVER (ORDER BY ts)
                        - 1 AS execution_return

                    FROM joined
                )
                SELECT
                    count(*) AS aligned_bars,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts,

                    percentile_cont(0.5)
                    WITHIN GROUP (
                        ORDER BY signal_close/execution_close
                    ) AS median_signal_execution_ratio,

                    corr(
                        signal_return::double precision,
                        execution_return::double precision
                    ) AS return_correlation

                FROM ret
                WHERE signal_return IS NOT NULL
                  AND execution_return IS NOT NULL
                """,
                (
                    SIGNAL_SYMBOL,
                    EXECUTION_SYMBOL,
                    TIMEFRAME,
                ),
            )
            aligned = dict(cur.fetchone() or {})

        signal_price = d(signal.get("median_close"))
        execution_price = d(execution.get("median_close"))

        tick_size = d(contract.get("tick_size"))
        tick_value = d(contract.get("tick_value"))
        buy_sell_fee = d(cost.get("buy_sell_fee"))

        rub_per_execution_point = (
            tick_value / tick_size
            if tick_size > 0
            else Decimal("0")
        )

        fee_round_trip_rub = (
            buy_sell_fee * Decimal("2")
        )

        slippage_round_trip_rub = (
            tick_value * Decimal("2")
        )

        round_trip_rub = (
            fee_round_trip_rub
            + slippage_round_trip_rub
        )

        execution_cost_points = (
            round_trip_rub / rub_per_execution_point
            if rub_per_execution_point > 0
            else Decimal("0")
        )

        # Только диагностическая пропорциональная оценка.
        # НЕ является разрешённой cost-моделью.
        price_ratio = (
            signal_price / execution_price
            if execution_price > 0
            else Decimal("0")
        )

        diagnostic_signal_cost_points = (
            execution_cost_points * price_ratio
        )

        corr = aligned.get("return_correlation")

        print(
            "PRICE_SCALE_ROW "
            f"signal_median_close={signal_price} "
            f"execution_median_close={execution_price} "
            f"price_ratio={price_ratio}"
        )

        print(
            "ALIGNMENT_ROW "
            f"aligned_bars={aligned.get('aligned_bars', 0)} "
            f"first_ts={aligned.get('first_ts')} "
            f"last_ts={aligned.get('last_ts')} "
            f"median_signal_execution_ratio="
            f"{aligned.get('median_signal_execution_ratio')} "
            f"return_correlation={corr}"
        )

        print(
            "COST_ROW "
            f"buy_sell_fee={buy_sell_fee} "
            f"tick_size={tick_size} "
            f"tick_value={tick_value} "
            f"round_trip_cost_rub={round_trip_rub} "
            f"execution_cost_points={execution_cost_points}"
        )

        print(
            "DIAGNOSTIC_SCALE_ROW "
            f"direct_signal_cost_points={execution_cost_points} "
            f"proportional_signal_cost_points="
            f"{diagnostic_signal_cost_points}"
        )

        direct_mapping_valid = (
            abs(price_ratio - Decimal("1"))
            <= Decimal("0.05")
        )

        correlation_sufficient = (
            corr is not None
            and float(corr) >= 0.90
        )

        print()
        print(
            f"direct_price_point_mapping_valid="
            f"{int(direct_mapping_valid)}"
        )
        print(
            f"return_mapping_sufficient="
            f"{int(correlation_sufficient)}"
        )

        print("economic_verdict_allowed=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if direct_mapping_valid:
            verdict = (
                "IMOEX2_MXU6_DIRECT_COST_SCALE_SUPPORTED"
            )
        elif correlation_sufficient:
            verdict = (
                "IMOEX2_MXU6_RETURN_MAPPING_REQUIRED"
            )
        else:
            verdict = (
                "IMOEX2_MXU6_PROXY_MAPPING_INSUFFICIENT"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
