from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


CONFIG = Path(
    "config/research/"
    "usdrubf_futures_cost_semantics_v1.json"
)


def dec(value) -> Decimal:
    return Decimal(str(value))


def main() -> int:
    cfg = json.loads(
        CONFIG.read_text()
    )

    lot = dec(
        cfg["contract_lot_underlying_units"]
    )

    tick_size = dec(
        cfg["tick_size"]
    )

    tick_value = dec(
        cfg["tick_value_rub"]
    )

    taker_rate_pct = dec(
        cfg[
            "ordinary_unaddressed_taker_rate_pct"
        ]
    )

    addressed_rate_pct = dec(
        cfg["addressed_rate_pct"]
    )

    maker_rate_pct = dec(
        cfg["maker_rate_pct"]
    )

    legacy = cfg["legacy_iss_fields"]

    buy_sell_fee = dec(
        legacy["buy_sell_fee"]
    )

    scalper_fee = dec(
        legacy["scalper_fee"]
    )

    negotiated_fee = dec(
        legacy["negotiated_fee"]
    )

    # Проверяем денежный масштаб.
    calculated_tick_value = (
        tick_size * lot
    )

    if calculated_tick_value != tick_value:
        raise RuntimeError(
            "ERROR=USDRUBF_TICK_VALUE_CONTRACT_MISMATCH "
            f"calculated={calculated_tick_value} "
            f"stored={tick_value}"
        )

    # pct → decimal fraction.
    taker_rate = (
        taker_rate_pct
        / Decimal("100")
    )

    addressed_rate = (
        addressed_rate_pct
        / Decimal("100")
    )

    maker_rate = (
        maker_rate_pct
        / Decimal("100")
    )

    # Какая цена базового актива делает ISS absolute fee
    # согласованным с текущей тарифной ставкой.
    implied_buy_sell_price = (
        buy_sell_fee
        / taker_rate
        / lot
    )

    implied_negotiated_price = (
        negotiated_fee
        / addressed_rate
        / lot
    )

    scalper_to_buy_sell_ratio = (
        scalper_fee
        / buy_sell_fee
    )

    fee_rate_ratio = (
        taker_rate
        / addressed_rate
    )

    iss_fee_ratio = (
        buy_sell_fee
        / negotiated_fee
    )

    print(
        "MONETARY_SCALE_ROW "
        f"symbol={cfg['symbol']} "
        f"lot_underlying_units={lot} "
        f"tick_size={tick_size} "
        f"tick_value_rub={tick_value} "
        f"calculated_tick_value_rub="
        f"{calculated_tick_value}"
    )

    print(
        "MOEX_FEE_RATE_ROW "
        f"maker_rate_pct={maker_rate_pct} "
        f"unaddressed_taker_rate_pct="
        f"{taker_rate_pct} "
        f"addressed_rate_pct="
        f"{addressed_rate_pct}"
    )

    print(
        "ISS_SEMANTICS_ROW "
        f"buy_sell_fee={buy_sell_fee} "
        f"implied_buy_sell_price="
        f"{implied_buy_sell_price} "
        f"negotiated_fee={negotiated_fee} "
        f"implied_negotiated_price="
        f"{implied_negotiated_price} "
        f"scalper_fee={scalper_fee} "
        f"scalper_to_buy_sell_ratio="
        f"{scalper_to_buy_sell_ratio}"
    )

    print(
        "RATE_CONSISTENCY_ROW "
        f"official_rate_ratio="
        f"{fee_rate_ratio} "
        f"iss_fee_ratio="
        f"{iss_fee_ratio}"
    )

    print(
        "FALLBACK_COST_CONTRACT "
        "actual_finam_fee_available=0 "
        "ordinary_fee_model=MOEX_MAKER_TAKER "
        "base_entry_role=TAKER "
        "base_exit_role=TAKER "
        "exercise_fee_included=0 "
        "funding_separate=1"
    )

    print(
        "canonical_monetary_scale="
        "PRICE_DELTA_X_1000_RUB"
    )

    print(
        "legacy_fixed_fee_fields_authoritative=0"
    )

    print(
        "db_writes_performed=0"
    )

    print(
        "runtime_changed=0"
    )

    print(
        "execution_changed=0"
    )

    print(
        "orders_changed=0"
    )

    print(
        "fills_changed=0"
    )

    print(
        "economic_edge_claimed=0"
    )

    print(
        "micro_live_allowed=0"
    )

    print(
        "VERDICT="
        "USDRUBF_FUTURES_COST_SEMANTICS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
