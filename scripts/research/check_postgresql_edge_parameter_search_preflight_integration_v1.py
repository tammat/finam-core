#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import pathlib
import sys


path = pathlib.Path(
    "scripts/research/build_postgresql_edge_parameter_search_v1.py"
)

spec = importlib.util.spec_from_file_location(
    "edge_parameter_search_builder_v1",
    path,
)

if spec is None or spec.loader is None:
    raise SystemExit("ERROR=builder_import_failed")

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

checks = {
    "SearchTask": hasattr(module, "SearchTask"),
    "insert_tasks": hasattr(module, "insert_tasks"),
    "SUPPORTED_STRATEGIES": hasattr(module, "SUPPORTED_STRATEGIES"),
    "validate_parameters": hasattr(module, "validate_parameters"),
}

for name, ready in checks.items():
    print(
        "INTEGRATION_IMPORT_CHECK "
        f"name={name} "
        f"ready={int(ready)}"
    )

if not all(checks.values()):
    raise SystemExit(
        "ERROR=integration_import_contract_incomplete"
    )

print("db_writes_performed=0")
print(
    "VERDICT="
    "POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_INTEGRATION_IMPORT_V1_OK"
)
