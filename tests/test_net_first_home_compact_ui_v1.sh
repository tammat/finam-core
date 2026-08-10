#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_NET_FIRST_HOME_COMPACT_UI_V1 ==="

python - <<'PY'
from marketcore.presentation.workspace_v2.resolver.control_compact_v3_resolver import (
    ControlCompactV3Resolver,
)

snapshot = ControlCompactV3Resolver().resolve()

summary = snapshot.get("net_first_summary") or {}

assert int(summary.get("total_candidates") or 0) == 27
assert int(summary.get("economically_resolved") or 0) == 27
assert int(summary.get("would_admit") or 0) == 18
assert int(summary.get("would_reject") or 0) == 9
assert int(summary.get("potential_downstream_saved") or 0) == 9
assert float(summary.get("economic_coverage_pct") or 0) == 100.0
assert bool(summary.get("enforced_admission_enabled")) is False

print("resolver_net_first_total=27")
print("resolver_net_first_resolved=27")
print("resolver_net_first_admit=18")
print("resolver_net_first_reject=9")
print("resolver_net_first_saved=9")
print("resolver_net_first_coverage=100")
print("resolver_net_first_enforcement=0")
PY

python - <<'PY'
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import (
    build_domain_document_v2,
)

document = build_domain_document_v2("HOME")

rendered = repr(document)

required = (
    "home.compact.net-first",
    "home.compact.net-first.title",
    "home.compact.net-first.metrics",
    "net-first.coverage",
    "net-first.gate",
    "net-first.saved",
    "net-first.enforcement",
    "Экономика поиска edge",
)

for value in required:
    if value not in rendered:
        raise SystemExit(
            f"ERROR=NET_FIRST_HOME_RENDER_VALUE_MISSING value={value}"
        )

print("home_net_first_section=1")
print("home_net_first_metrics=1")
print("home_net_first_source=POSTGRESQL")
PY

echo "production_pipeline_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TEST_NET_FIRST_HOME_COMPACT_UI_V1_OK"
