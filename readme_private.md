# Finam_Core (Private Prop Engine)

## Status
v1.0-core-baseline

Execution + Accounting stable.
No double counting.
Equity = cash + unrealized.

## Architecture

Signal → Order → Fill → Position → Portfolio → Risk

## Current Capabilities
- Event-driven core
- OMS with FillEvent
- Institutional accounting model
- Drawdown tracking
- Exposure tracking
- Risk pre-trade checks

## Roadmap (internal)
1. Partial fill model
2. Slippage & latency simulation
3. Margin engine
4. Correlation risk
5. Event-store
6. Deterministic replay