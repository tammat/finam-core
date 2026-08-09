#!/usr/bin/env python3
"""
IMOEX2_EXECUTION_MAPPING_AUDIT_V1

Read-only аудит execution mapping:

    IMOEX2 -> MXU6@RTSX

Разделяет:
1. существование reference series;
2. существование tradable execution proxy;
3. contract specification;
4. cost specification;
5. canonical underlying/alias mapping.

Никаких изменений runtime/execution.
"""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


REFERENCE_SYMBOL = "IMOEX2"
EXECUTION_SYMBOL = "MXU6@RTSX"


def fetch_one(cur, sql: str, params: tuple) -> dict:
    cur.execute(sql, params)
    return dict(cur.fetchone() or {})


def main() -> int:
    print("=== IMOEX2 EXECUTION MAPPING AUDIT V1 ===")
    print("mode=research_read_only")
    print(f"reference_symbol={REFERENCE_SYMBOL}")
    print(f"execution_symbol={EXECUTION_SYMBOL}")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            reference = fetch_one(
                cur,
                """
                SELECT
                    count(*) AS bars,
                    count(DISTINCT ts::date) AS trading_days,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe='M5'
                """,
                (REFERENCE_SYMBOL,),
            )

            execution_bars = fetch_one(
                cur,
                """
                SELECT
                    count(*) AS bars,
                    count(DISTINCT ts::date) AS trading_days,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe='M5'
                """,
                (EXECUTION_SYMBOL,),
            )

            instrument = fetch_one(
                cur,
                """
                SELECT
                    symbol,
                    display_name,
                    asset_class,
                    exchange,
                    board,
                    currency,
                    lot_size,
                    min_price_step,
                    contract_size,
                    expiration_date,
                    underlying_symbol,
                    is_active,
                    is_tradable,
                    source,
                    source_version
                FROM marketcore.instrument_reference_v1
                WHERE symbol=%s
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )

            market_instrument = fetch_one(
                cur,
                """
                SELECT
                    symbol,
                    exchange_code,
                    asset_class,
                    currency_code,
                    instrument_name,
                    is_active,
                    eligibility_scope,
                    source_version
                FROM analytics.market_instrument_v1
                WHERE symbol=%s
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )

            contract = fetch_one(
                cur,
                """
                SELECT
                    symbol,
                    lot_size,
                    tick_size,
                    tick_value,
                    contract_multiplier,
                    price_precision,
                    valid_from,
                    valid_to,
                    is_active,
                    source_version
                FROM analytics.market_contract_spec_v1
                WHERE symbol=%s
                  AND is_active=true
                ORDER BY valid_from DESC
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )

            execution_spec = fetch_one(
                cur,
                """
                SELECT
                    symbol,
                    quantity_step,
                    underlying_units,
                    source_version,
                    updated_at
                FROM analytics.market_contract_execution_spec_v2
                WHERE symbol=%s
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )

            cost = fetch_one(
                cur,
                """
                SELECT
                    symbol,
                    initial_margin,
                    buy_sell_fee,
                    scalper_fee,
                    negotiated_fee,
                    exercise_fee,
                    fee_currency,
                    source_version,
                    verified_at
                FROM analytics.market_contract_cost_spec_v1
                WHERE symbol=%s
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )

            alias = fetch_one(
                cur,
                """
                SELECT
                    canonical_symbol,
                    execution_symbol,
                    feed_symbol,
                    root_symbol,
                    enabled,
                    reason
                FROM analytics.futures_symbol_alias_v1
                WHERE execution_symbol=%s
                   OR canonical_symbol=%s
                   OR feed_symbol=%s
                LIMIT 1
                """,
                (
                    EXECUTION_SYMBOL,
                    REFERENCE_SYMBOL,
                    REFERENCE_SYMBOL,
                ),
            )

            universe = fetch_one(
                cur,
                """
                SELECT
                    root_symbol,
                    contract_symbol,
                    asset_class,
                    expiration_date,
                    is_active,
                    roll_priority,
                    status
                FROM public.futures_contract_universe
                WHERE contract_symbol=%s
                LIMIT 1
                """,
                (EXECUTION_SYMBOL,),
            )

        reference_ready = (
            int(reference.get("bars") or 0) >= 6000
        )

        execution_series_ready = (
            int(execution_bars.get("bars") or 0) >= 6000
        )

        tradable_confirmed = (
            instrument.get("is_active") is True
            and instrument.get("is_tradable") is True
            and str(instrument.get("asset_class") or "").upper()
                in {"FUTURE", "FUTURES"}
        )

        contract_spec_confirmed = (
            contract.get("is_active") is True
            and contract.get("tick_size") is not None
            and contract.get("tick_value") is not None
        )

        cost_spec_confirmed = (
            cost.get("buy_sell_fee") is not None
            and cost.get("verified_at") is not None
        )

        research_eligible = (
            market_instrument.get("eligibility_scope")
            == "RESEARCH"
        )

        # Canonical relation deliberately requires explicit
        # alias/underlying evidence, not ticker inference.
        canonical_mapping_confirmed = bool(alias) or (
            str(instrument.get("underlying_symbol") or "").strip()
            in {
                "IMOEX",
                "IMOEX2",
            }
        )

        # Proxy status can be confirmed independently from
        # canonical underlying identity.
        proxy_confirmed = (
            reference_ready
            and execution_series_ready
            and tradable_confirmed
            and contract_spec_confirmed
            and cost_spec_confirmed
            and research_eligible
            and str(instrument.get("source_version") or "")
                == "MXU6_EXECUTION_PROXY_V1"
        )

        print(
            "REFERENCE_ROW "
            f"symbol={REFERENCE_SYMBOL} "
            f"m5_bars={reference.get('bars', 0)} "
            f"trading_days={reference.get('trading_days', 0)} "
            f"ready={int(reference_ready)}"
        )

        print(
            "EXECUTION_SERIES_ROW "
            f"symbol={EXECUTION_SYMBOL} "
            f"m5_bars={execution_bars.get('bars', 0)} "
            f"trading_days={execution_bars.get('trading_days', 0)} "
            f"ready={int(execution_series_ready)}"
        )

        print(
            "INSTRUMENT_ROW "
            f"symbol={EXECUTION_SYMBOL} "
            f"name={instrument.get('display_name')} "
            f"asset_class={instrument.get('asset_class')} "
            f"is_active={instrument.get('is_active')} "
            f"is_tradable={instrument.get('is_tradable')} "
            f"eligibility_scope={market_instrument.get('eligibility_scope')} "
            f"source_version={instrument.get('source_version')}"
        )

        print(
            "CONTRACT_ROW "
            f"tick_size={contract.get('tick_size')} "
            f"tick_value={contract.get('tick_value')} "
            f"lot_size={contract.get('lot_size')} "
            f"multiplier={contract.get('contract_multiplier')} "
            f"expiration_date={instrument.get('expiration_date')} "
            f"confirmed={int(contract_spec_confirmed)}"
        )

        print(
            "COST_ROW "
            f"initial_margin={cost.get('initial_margin')} "
            f"buy_sell_fee={cost.get('buy_sell_fee')} "
            f"scalper_fee={cost.get('scalper_fee')} "
            f"currency={cost.get('fee_currency')} "
            f"verified_at={cost.get('verified_at')} "
            f"confirmed={int(cost_spec_confirmed)}"
        )

        print(
            "UNIVERSE_ROW "
            f"root_symbol={universe.get('root_symbol')} "
            f"status={universe.get('status')} "
            f"is_active={universe.get('is_active')} "
            f"roll_priority={universe.get('roll_priority')}"
        )

        print(
            "MAPPING_EVIDENCE "
            f"alias_found={int(bool(alias))} "
            f"underlying_symbol="
            f"{instrument.get('underlying_symbol') or 'NONE'} "
            f"proxy_source_version="
            f"{instrument.get('source_version') or 'NONE'}"
        )

        print()
        print(f"reference_ready={int(reference_ready)}")
        print(
            f"execution_series_ready="
            f"{int(execution_series_ready)}"
        )
        print(
            f"tradable_instrument_confirmed="
            f"{int(tradable_confirmed)}"
        )
        print(
            f"contract_spec_confirmed="
            f"{int(contract_spec_confirmed)}"
        )
        print(
            f"cost_spec_confirmed="
            f"{int(cost_spec_confirmed)}"
        )
        print(
            f"research_eligible="
            f"{int(research_eligible)}"
        )
        print(
            f"execution_proxy_confirmed="
            f"{int(proxy_confirmed)}"
        )
        print(
            f"canonical_mapping_confirmed="
            f"{int(canonical_mapping_confirmed)}"
        )

        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if proxy_confirmed and canonical_mapping_confirmed:
            verdict = (
                "IMOEX2_EXECUTION_MAPPING_CONFIRMED"
            )
        elif proxy_confirmed:
            verdict = (
                "IMOEX2_EXECUTION_PROXY_CONFIRMED_"
                "CANONICAL_LINK_PENDING"
            )
        else:
            verdict = (
                "IMOEX2_EXECUTION_MAPPING_NOT_READY"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
