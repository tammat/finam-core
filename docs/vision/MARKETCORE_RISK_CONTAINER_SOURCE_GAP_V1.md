# MarketCore Risk Container Source Gap V1

## Decision

`container.risk` remains without a ready V2 producer. The current portfolio sources do not publish the mandatory Risk KPIs as governed domain facts.

## Verified sources

- `public.v_real_portfolio_summary_ru`: portfolio value, total PnL, daily PnL, position count, timestamp.
- `presentation.v_workspace_v2_portfolio_positions_ru`: position quantity, prices, valuation, PnL and update time.
- `public.v_positions_dashboard_ru`: instrument identity, quantity, average price, realized PnL and update time.
- `public.v_portfolio_visualization_ru`: position quantity, valuation and realized PnL.

## Missing governed outputs

- exposure KPI;
- concentration KPI;
- correlation KPI;
- drawdown KPI;
- risk budget;
- available risk.

The presentation layer must not derive these metrics. A Risk-owned resolver must define sources, formulas, timestamps, quality codes and empty/failure semantics before the container is marked ready.

## Exit gate

`container.risk` may receive a producer only after a test proves that all published Risk values come from the governed Risk resolver and that unavailable values are not replaced with zero.

`VERDICT=MARKETCORE_RISK_CONTAINER_SOURCE_GAP_CONFIRMED`
