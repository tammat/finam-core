# Finam_Core

Production-grade event-driven trading platform for Finam / MOEX.

## Current Architecture Level

Finam_Core is no longer a simple trading bot.
It is an execution and recovery platform with:

- event-driven market pipeline;
- centralized RiskStack;
- isolated ExecutionDispatcher;
- OMS with finite state machine;
- PostgreSQL order journal;
- persistent kill switch;
- startup recovery gate;
- broker reconciliation;
- EventStore;
- replay reader;
- recovery snapshots;
- snapshot-aware portfolio rebuild.

## Documentation

| Document | Purpose |
|---|---|
| docs/ARCHITECTURE.md | System architecture |
| docs/EXECUTION.md | Execution routing |
| docs/OMS.md | Order management system |
| docs/RECOVERY.md | Recovery pipeline |
| docs/EVENT_STORE.md | Event sourcing and audit |
| docs/RISK_STACK.md | Risk controls |
| docs/RUNBOOK.md | Operational commands |

## Safety First

Real futures trading is blocked by design until explicitly enabled.

Current real execution chain:

```text
PersistentKillSwitch
-> FuturesAccessGate
-> FuturesMarginGuard
-> OmsDispatchGuard
-> RealExecutionEngine
```
