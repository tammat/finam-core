Finam_Core

Event‑sourced deterministic trading engine core.

Stable write‑side infrastructure for multi‑asset portfolio management with strict consistency guarantees.

⸻

Version

v1.4 – Stable Event Core (Write‑Side Baseline)
Tag: v1.4

⸻

Architecture Overview

Finam_Core implements a deterministic event‑sourced write‑side engine.

Core principles:
	•	Append‑first persistence boundary
	•	Optimistic concurrency (versioned streams)
	•	Idempotent event storage
	•	Deterministic replay
	•	Snapshot bootstrap
	•	Restart‑safe engine

No handler executes before event persistence.

⸻

Project Structure

core/
  events/
  event_bus.py

execution/
  trading_engine.py

storage/
  postgres_event_store.py
  postgres_snapshot_store.py

risk/
  pre_trade_risk_engine.py

tests/


⸻

Event Flow

StrategySignalEvent
        ↓
EventBus.publish()
        ↓
PostgresEventStore.append()
        ↓
Synchronous handlers

Persistence is the consistency boundary.

⸻

Database Schema

Events

CREATE TABLE events (
    id UUID PRIMARY KEY,
    stream TEXT NOT NULL,
    type TEXT NOT NULL,
    version BIGINT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_events_stream_version
ON events(stream, version);

Snapshots

CREATE TABLE snapshots (
    stream TEXT PRIMARY KEY,
    version BIGINT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);


⸻

Consistency Guarantees

Feature	Status
Append‑first	✅
Optimistic concurrency	✅
Idempotent event_id	✅
Deterministic replay	✅
Snapshot restore	✅
Restart‑safe engine	✅


⸻

Core Tests
	•	test_engine_restart_simulation
	•	test_snapshot_bootstrap
	•	test_idempotent_append

All tests passing in v1.4.

⸻

Deterministic Replay Model

State reconstruction procedure:
	1.	Load snapshot (if exists)
	2.	Replay events ordered by (stream, version)
	3.	Rebuild PortfolioState

Replay must produce identical state after restart.

⸻

Configuration

Environment variable required:

POSTGRES_DSN=postgresql://user:password@localhost:5432/finam_core

No hardcoded DSN allowed in source code.

⸻

Design Constraints (Frozen in v1.4)
	•	Event IDs are generated inside event objects
	•	Storage never mutates event identity
	•	No async dispatch inside write boundary
	•	Version increments strictly monotonic per stream
	•	Append‑first invariant must not be violated

Event contract is frozen at this version.

⸻

Scope of v1.4

Included:
	•	Write‑side event sourcing
	•	Persistence guarantees
	•	Snapshot bootstrap
	•	Deterministic restart safety

Not included:
	•	Advanced risk aggregation
	•	Correlation exposure limits
	•	Portfolio optimization
	•	AI signal layer
	•	Read‑side projections

⸻

Roadmap

v1.5 – Deterministic Risk Engine
	•	Position sizing rules
	•	Exposure limits
	•	Daily loss cap

v1.6 – Multi‑Asset Aggregation
	•	Correlation clusters
	•	Cross‑asset exposure control

v1.7 – Read‑Side Projections
	•	Analytics
	•	Monitoring

v2.0 – AI‑Ready Portfolio Layer
	•	Feature store
	•	ML integration

⸻

Architectural Status

v1.4 establishes a stable, production‑grade write‑side core.

All future changes must preserve:
	•	Append‑first boundary
	•	Event immutability
	•	Idempotent storage
	•	Deterministic replay

Tag v1.4 is the canonical infrastructure baseline.