from __future__ import annotations

from finam_core.runtime.adaptive_capital_allocator_v2 import (
    AdaptiveCapitalAllocatorV2,
)

def main() -> int:

    decision = AdaptiveCapitalAllocatorV2().decide(
        trade_quality_score=84,
        expected_value=2.3,
        probability_tp=0.63,
        probability_sl=0.34,
        market_breadth=0.71,
        runtime_stress_level="INFO",
        portfolio_drawdown_pct=0.02,
        correlation_pressure=0.25,
        runtime_regime="trend_up_high_vol",
    )

    print(
        "ADAPTIVE_CAPITAL_ALLOCATOR_V2 "
        f"allowed={decision.allowed} "
        f"capital_multiplier={decision.capital_multiplier:.2f} "
        f"allocation_pct={decision.allocation_pct:.2f} "
        f"reason={decision.reason}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
