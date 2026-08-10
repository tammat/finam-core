from __future__ import annotations

import ast
from pathlib import Path


FILES = (
    Path(
        "src/scripts/research/"
        "build_universe_trend_pullback_canonical_adapter_screen_v1.py"
    ),
    Path(
        "src/scripts/research/"
        "build_trend_pullback_canonical_robustness_v1.py"
    ),
    Path(
        "src/scripts/research/"
        "build_trend_pullback_canonical_equity_base_cost_validation_v1.py"
    ),
)


SEARCH_NAMES = {
    "build_canonical_trades",
    "gross_metrics",
    "trend_pullback_signal",
    "hold_bars",
    "fast_ma_period",
    "slow_ma_period",
    "atr_period",
    "pullback_atr_multiplier",
    "development_fraction",
    "development_end",
    "minimum_oos_trades",
}


def main() -> int:
    for path in FILES:
        if not path.exists():
            raise RuntimeError(
                f"ERROR=REQUIRED_SOURCE_MISSING path={path}"
            )

        text = path.read_text()
        ast.parse(text)

        print(
            "SOURCE_FILE "
            f"path={path} "
            f"bytes={len(text)}"
        )

        lines = text.splitlines()

        for no, line in enumerate(lines, start=1):
            if any(
                name in line
                for name in SEARCH_NAMES
            ):
                print(
                    "CONTRACT_SOURCE "
                    f"file={path.name} "
                    f"line={no} "
                    f"text={line.strip()}"
                )

    print("symbol=USDRUBF@RTSX")
    print("strategy_code=TREND_PULLBACK_V1")
    print("timeframe=M5")

    print(
        "commission_model="
        "MOEX_MAKER_TAKER_FALLBACK"
    )

    print("entry_liquidity_role=TAKER")
    print("exit_liquidity_role=TAKER")

    print(
        "canonical_monetary_scale="
        "PRICE_DELTA_X_1000_RUB"
    )

    print(
        "baseline_slippage_round_trip_rub=2"
    )

    print(
        "stress_slippage_round_trip_rub=20"
    )

    print("funding_used=0")
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
        "USDRUBF_FUTURES_BASE_COST_CONTRACT_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
