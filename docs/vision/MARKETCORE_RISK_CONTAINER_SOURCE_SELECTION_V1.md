# MarketCore Risk Container Source Selection V1

## Governed sources

Primary portfolio risk source: `public.portfolio_risk_state`.

It owns cluster heat, portfolio share, risk state, reason and `calculated_at`.

Supporting sources:

- `marketcore_ui.risk_summary_v1` owns runtime/execution permissions, daily risk percent and `refreshed_at`;
- `analytics.risk_decision_snapshot_v1` owns position, exposure, daily-loss, correlation and aggregate risk scores per decision.

`public.analytics_drawdown_summary` is research/backtest evidence and must not be presented as current portfolio drawdown.

## Freshness

Every value keeps its source timestamp and identity. The container is `WARNING` when a source exceeds its governed freshness window and must never convert stale data into a green recommendation.

Missing values remain `UNAVAILABLE`; zero is allowed only when zero is explicitly stored by the owning source.

## Superseded gap

The earlier source-gap audit correctly proved that generic Portfolio views were insufficient. This selection closes the source discovery gap by using Risk-owned sources; it does not mark the Risk container complete.

`VERDICT=MARKETCORE_RISK_CONTAINER_SOURCES_SELECTED`
