#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/workspace_v2/domain/risk_snapshot_v2.py src/marketcore/presentation/workspace_v2/resolver/risk_v2_resolver.py
PYTHONPATH=src .venv/bin/python - <<'PY'
from datetime import datetime, timezone
from marketcore.presentation.workspace_v2.resolver.risk_v2_resolver import RiskV2Resolver
s=RiskV2Resolver().resolve(generated_at=datetime(2026,7,15,12,tzinfo=timezone.utc))
assert s.maximum_age_seconds > 0
assert s.clusters and s.permissions and s.decisions.decisions_total > 0
assert s.portfolio_freshness_code == s.permission_freshness_code == s.decision_freshness_code == "STALE"
assert s.permissions.runtime_allowed is False and s.permissions.execution_allowed is False
print(f"risk_clusters={len(s.clusters)}")
print(f"risk_decisions={s.decisions.decisions_total}")
print("freshness=STALE")
print("VERDICT=MARKETCORE_RISK_V2_RESOLVER_READY")
PY
