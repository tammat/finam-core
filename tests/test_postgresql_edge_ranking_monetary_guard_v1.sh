#!/usr/bin/env bash
set -euo pipefail

SEARCH="scripts/research/run_postgresql_edge_parameter_search_v1.py"

echo "=== TEST_POSTGRESQL_EDGE_RANKING_MONETARY_GUARD_V1 ==="

PYTHONPATH=src python -m py_compile \
  "$SEARCH" \
  src/finam_core/research/futures_monetary_validity_v1.py

PYTHONPATH=src python - <<'PY'
from __future__ import annotations

import importlib.util
from pathlib import Path


path = Path(
    "scripts/research/"
    "run_postgresql_edge_parameter_search_v1.py"
)

spec = importlib.util.spec_from_file_location(
    "run_postgresql_edge_parameter_search_v1",
    path,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

guard = module.apply_monetary_ranking_guard

lineage = {
    "valid": {
        "monetary_status": "VALID_MONETARY",
        "ranking_allowed": True,
    },
    "invalid": {
        "monetary_status": "LEGACY_INVALID_MONETARY",
        "ranking_allowed": False,
    },
    "no_spec": {
        "monetary_status": "UNRESOLVED_NO_SPEC",
        "ranking_allowed": False,
    },
    "cbr": {
        "monetary_status": "UNRESOLVED_CBR_MONETARY",
        "ranking_allowed": False,
    },
}


def apply(
    symbol: str,
    run_uuid: str,
    classification: str,
    reason: str,
) -> tuple[str, str]:
    return guard(
        symbol=symbol,
        run_uuid=run_uuid,
        classification=classification,
        reason=reason,
        monetary_by_run=lineage,
    )


# Equity candidate не затрагивается.
assert apply(
    "SBER@MISX",
    "missing",
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
) == (
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
)

# VALID_MONETARY futures допускается.
assert apply(
    "NGZ6@RTSX",
    "valid",
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
) == (
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
)

# Доказанный monetary mismatch блокируется.
assert apply(
    "BRZ6@RTSX",
    "invalid",
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
) == (
    "MONETARY_VALIDITY_REJECTED",
    "LEGACY_INVALID_MONETARY",
)

# Отсутствующий exact spec блокируется.
assert apply(
    "NGK6@RTSX",
    "no_spec",
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
) == (
    "MONETARY_VALIDITY_REJECTED",
    "UNRESOLVED_NO_SPEC",
)

# Неаудированный CBR monetary path блокируется.
assert apply(
    "BRZ6@RTSX",
    "cbr",
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
) == (
    "MONETARY_VALIDITY_REJECTED",
    "UNRESOLVED_CBR_MONETARY",
)

# Отсутствующий lineage всегда fail-closed.
assert apply(
    "NGZ6@RTSX",
    "missing",
    "EDGE_CANDIDATE",
    "POSITIVE_AFTER_COSTS",
) == (
    "MONETARY_VALIDITY_REJECTED",
    "MONETARY_LINEAGE_MISSING",
)

# Monetary guard не уничтожает первичную причину rejection.
assert apply(
    "NGZ6@RTSX",
    "valid",
    "REJECTED_AFTER_COSTS",
    "EXPECTANCY_NOT_POSITIVE",
) == (
    "REJECTED_AFTER_COSTS",
    "EXPECTANCY_NOT_POSITIVE",
)

print("equity_candidate_preserved=1")
print("valid_futures_candidate_allowed=1")
print("invalid_futures_candidate_blocked=1")
print("unresolved_no_spec_blocked=1")
print("unresolved_cbr_blocked=1")
print("missing_lineage_fail_closed=1")
print("primary_rejection_reason_preserved=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TEST_POSTGRESQL_EDGE_RANKING_MONETARY_GUARD_V1_OK"
)
PY
