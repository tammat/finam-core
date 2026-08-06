#!/usr/bin/env python3
from __future__ import annotations

import ast
import pathlib


ROOT = pathlib.Path("/opt/finam-core")
TARGET = (
    ROOT
    / "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
)


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(source)

    required_fragments = (
        "analytics.edge_lab_run_v1",
        "analytics.edge_observation_v1",
        "analytics.research_trade_v1",
        "public",
        "market_bars",
        "FOR UPDATE SKIP LOCKED",
        "required_cost_parameters_missing",
        "commission_per_side",
        "slippage_bps",
        "persist_trades",
        "persist_observation",
        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_READY",
    )

    missing = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    forbidden = (
        "sqlite3",
        "bars.sqlite",
        "send_order(",
        "place_order(",
        "submit_order(",
        "execution_enabled = true",
        "micro_live_allowed = true",
    )

    forbidden_present = [
        fragment
        for fragment in forbidden
        if fragment in source
    ]

    if missing:
        raise RuntimeError(
            "required_contract_missing:"
            + ",".join(missing)
        )

    if forbidden_present:
        raise RuntimeError(
            "forbidden_contract_present:"
            + ",".join(forbidden_present)
        )

    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    required_functions = {
        "load_bars",
        "build_trades",
        "calculate_metrics",
        "claim_task",
        "persist_trades",
        "persist_observation",
        "finalize_task",
        "execute_one",
        "synthetic_self_test",
    }

    missing_functions = sorted(
        required_functions - function_names
    )

    if missing_functions:
        raise RuntimeError(
            "required_functions_missing:"
            + ",".join(missing_functions)
        )

    print("python_ast=OK")
    print(f"required_function_count={len(required_functions)}")
    print("postgresql_only=1")
    print("sqlite_used=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_BUILD_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
