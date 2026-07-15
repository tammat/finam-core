#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.presentation.navigation.container_registry_v2 import resolve_container_v2
from marketcore.presentation.workspace_v2.resolver.portfolio_v2_resolver import PortfolioV2Resolver

risk = resolve_container_v2("container.risk")
assert risk.target_ready is False
assert risk.producer_code is None

snapshot = PortfolioV2Resolver().resolve()
columns = {
    str(column).strip().lower()
    for group in (snapshot.summary, snapshot.positions, snapshot.dashboard, snapshot.visualization)
    for row in group
    for column in row.values
}
required = {"exposure", "concentration", "correlation", "drawdown", "risk budget", "available risk"}
assert not required.intersection(columns)
assert snapshot.summary and snapshot.positions
print(f"observed_source_columns={len(columns)}")
print("governed_risk_kpis=0")
print("risk_target_ready=0")
print("false_zero_allowed=0")
print("VERDICT=MARKETCORE_RISK_CONTAINER_SOURCE_GAP_CONFIRMED")
PY

grep -q 'presentation layer must not derive' docs/vision/MARKETCORE_RISK_CONTAINER_SOURCE_GAP_V1.md
