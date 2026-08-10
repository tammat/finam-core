from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor


SOURCE_VERSION = "TREND_PULLBACK_CANONICAL_COST_RESOLVER_V1"


@dataclass(frozen=True)
class CostContract:
    symbol: str
    asset_class: str
    exchange_code: str

    commission_per_trade: Decimal | None
    commission_pct: Decimal | None
    slippage_per_trade: Decimal | None

    commission_source: str
    slippage_source: str

    contract_buy_sell_fee: Decimal | None
    contract_scalper_fee: Decimal | None
    contract_negotiated_fee: Decimal | None
    contract_fee_source: str | None

    evidence_status: str


def dec(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def classify_symbol(symbol: str) -> tuple[str, str]:
    if symbol.endswith("@MISX"):
        return "EQUITY", "MISX"

    if symbol.endswith("@RTSX"):
        return "FUTURES", "RTSX"

    raise RuntimeError(
        f"ERROR=UNSUPPORTED_SYMBOL_CLASSIFICATION symbol={symbol}"
    )


def resolve_cost_contract(cur, symbol: str) -> CostContract:
    asset_class, exchange_code = classify_symbol(symbol)

    cur.execute(
        """
        SELECT
            commission_per_trade,
            commission_pct,
            source_version
        FROM analytics.commission_model_v1
        WHERE enabled = true
          AND asset_class = %s
          AND symbol_pattern = %s
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (
            asset_class,
            f"*@{exchange_code}",
        ),
    )

    commission_row = cur.fetchone()

    cur.execute(
        """
        SELECT
            slippage_per_trade,
            source_version
        FROM analytics.slippage_profile_v1
        WHERE is_active = true
          AND exchange_code = %s
          AND asset_class = %s
          AND liquidity_bucket = 'DEFAULT'
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (
            exchange_code,
            asset_class,
        ),
    )

    slippage_row = cur.fetchone()

    cur.execute(
        """
        SELECT
            buy_sell_fee,
            scalper_fee,
            negotiated_fee,
            source_version
        FROM analytics.market_contract_cost_spec_v1
        WHERE symbol = %s
        ORDER BY verified_at DESC
        LIMIT 1
        """,
        (symbol,),
    )

    contract_row = cur.fetchone()

    commission_per_trade = (
        dec(commission_row["commission_per_trade"])
        if commission_row
        else None
    )

    commission_pct = (
        dec(commission_row["commission_pct"])
        if commission_row
        else None
    )

    slippage_per_trade = (
        dec(slippage_row["slippage_per_trade"])
        if slippage_row
        else None
    )

    buy_sell_fee = (
        dec(contract_row["buy_sell_fee"])
        if contract_row
        else None
    )

    scalper_fee = (
        dec(contract_row["scalper_fee"])
        if contract_row
        else None
    )

    negotiated_fee = (
        dec(contract_row["negotiated_fee"])
        if contract_row
        else None
    )

    if asset_class == "EQUITY":
        complete = (
            commission_row is not None
            and slippage_row is not None
        )

        evidence_status = (
            "COST_SOURCE_COMPLETE"
            if complete
            else "COST_SOURCE_INCOMPLETE"
        )

    else:
        # Futures fail closed:
        # contract-specific fees существуют,
        # но их round-trip semantics ещё не подтверждены.
        evidence_status = (
            "FUTURES_CONTRACT_FEE_SEMANTICS_PENDING"
            if contract_row is not None
            else "COST_SOURCE_INCOMPLETE"
        )

    return CostContract(
        symbol=symbol,
        asset_class=asset_class,
        exchange_code=exchange_code,

        commission_per_trade=commission_per_trade,
        commission_pct=commission_pct,
        slippage_per_trade=slippage_per_trade,

        commission_source=(
            commission_row["source_version"]
            if commission_row
            else "MISSING"
        ),
        slippage_source=(
            slippage_row["source_version"]
            if slippage_row
            else "MISSING"
        ),

        contract_buy_sell_fee=buy_sell_fee,
        contract_scalper_fee=scalper_fee,
        contract_negotiated_fee=negotiated_fee,
        contract_fee_source=(
            contract_row["source_version"]
            if contract_row
            else None
        ),

        evidence_status=evidence_status,
    )


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit("ERROR=DATABASE_URL_NOT_SET")

    symbols = (
        "NVTK@MISX",
        "PLZL@MISX",
        "USDRUBF@RTSX",
    )

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            for symbol in symbols:
                contract = resolve_cost_contract(
                    cur,
                    symbol,
                )

                print(
                    "COST_CONTRACT_ROW "
                    f"symbol={contract.symbol} "
                    f"asset_class={contract.asset_class} "
                    f"exchange={contract.exchange_code} "
                    f"commission_per_trade="
                    f"{contract.commission_per_trade} "
                    f"commission_pct="
                    f"{contract.commission_pct} "
                    f"slippage_per_trade="
                    f"{contract.slippage_per_trade} "
                    f"buy_sell_fee="
                    f"{contract.contract_buy_sell_fee} "
                    f"scalper_fee="
                    f"{contract.contract_scalper_fee} "
                    f"negotiated_fee="
                    f"{contract.contract_negotiated_fee} "
                    f"status={contract.evidence_status}"
                )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_COST_RESOLVER_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
