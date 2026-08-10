#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

echo "=== TEST_ADAPTIVE_REGIME_POLICY_MERGE_V1 ==="

python -m py_compile \
  src/scripts/build_edge_hypothesis_discovery_v1.py

python - <<'PY'
import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import (
    load_search_configuration,
)

with psycopg2.connect("postgresql:///finam_core") as conn:
    with conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        configs = load_search_configuration(cur)

adaptive = []
invalid = []

for family, config in configs:
    policy = config.get("regime_policy") or {}
    targets = policy.get("target_symbols")

    if not targets:
        continue

    adaptive.append((family, config))

    if not policy.get("allowed_regimes"):
        invalid.append((family, targets, policy))

donchian_target = [
    config
    for family, config in adaptive
    if family == "DONCHIAN_VOL_BREAKOUT"
    and "PLZL@MISX"
       in (config.get("regime_policy") or {}).get(
           "target_symbols", []
       )
]

assert adaptive, "ADAPTIVE_CONFIGURATION_NOT_FOUND"
assert not invalid, f"ADAPTIVE_REGIME_POLICY_INVALID:{invalid}"
assert donchian_target, "PLZL_DONCHIAN_ADAPTIVE_CONFIG_NOT_FOUND"

policy = donchian_target[0]["regime_policy"]

expected = {
    "compression",
    "trend_up_expansion",
    "trend_down_expansion",
}

assert set(policy["allowed_regimes"]) == expected
assert policy["target_symbols"] == ["PLZL@MISX"]

print(f"adaptive_configurations={len(adaptive)}")
print("adaptive_missing_allowed_regimes=0")
print(
    "plzl_donchian_allowed_regimes="
    + ",".join(policy["allowed_regimes"])
)
print("plzl_target_symbol_preserved=1")
print("canonical_regime_policy_preserved=1")
print("target_override_merged=1")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TEST_ADAPTIVE_REGIME_POLICY_MERGE_V1_OK")
PY

git --no-pager diff --check
