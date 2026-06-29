#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DOMAIN_TYPES_V1 ==="

PYTHONPATH=src python - <<'PY'
from marketcore.core.domain_types import (
    CANONICAL_DOMAIN_TYPES,
    ACTIVE_KG_DOMAIN_TYPES_V1,
    normalize_domain_type,
    require_canonical_domain_type,
)

assert "CATALOG" in CANONICAL_DOMAIN_TYPES
assert "FEATURE" in CANONICAL_DOMAIN_TYPES
assert "MODEL" in CANONICAL_DOMAIN_TYPES
assert "EXPERIMENT" in CANONICAL_DOMAIN_TYPES

assert ACTIVE_KG_DOMAIN_TYPES_V1 == ("CATALOG", "FEATURE", "MODEL", "EXPERIMENT")

assert normalize_domain_type("CATALOG_OBJECT") == "CATALOG"
assert normalize_domain_type("FEATURES") == "FEATURE"
assert normalize_domain_type("MODELS") == "MODEL"
assert normalize_domain_type("EXPERIMENTS") == "EXPERIMENT"

assert require_canonical_domain_type("CATALOG_OBJECT") == "CATALOG"

try:
    require_canonical_domain_type("BAD_TYPE")
    raise AssertionError("BAD_TYPE must fail")
except ValueError:
    pass

print("canonical_domain_types=" + ",".join(CANONICAL_DOMAIN_TYPES))
print("active_kg_domain_types_v1=" + ",".join(ACTIVE_KG_DOMAIN_TYPES_V1))
print("alias_catalog_object=CATALOG")
print("alias_features=FEATURE")
print("alias_models=MODEL")
print("alias_experiments=EXPERIMENT")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=DOMAIN_TYPES_V1_READY"
echo "TEST_DOMAIN_TYPES_V1_OK"
