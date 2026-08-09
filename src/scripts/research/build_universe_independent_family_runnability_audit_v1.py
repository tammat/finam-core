#!/usr/bin/env python3
"""
UNIVERSE_INDEPENDENT_FAMILY_RUNNABILITY_AUDIT_V1

Read-only audit реальной исполнимости независимых strategy families.

Проверяет:
1. implementation существует;
2. runnable entrypoint существует;
3. config существует, если он требуется;
4. есть evidence signal generator / strategy code;
5. отделяет самостоятельные signal families от context/conditioning layers.

Ничего не запускает.
Не выполняет backtest.
Не ищет параметры.
Не пишет в PostgreSQL.
Не меняет runtime/execution.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


ROOT = Path("/opt/finam-core")


@dataclass(frozen=True)
class FamilyContract:
    family: str
    implementation_paths: tuple[str, ...]
    entrypoint_paths: tuple[str, ...]
    config_paths: tuple[str, ...]
    required_tokens: tuple[str, ...]
    classification: str


CONTRACTS = (
    FamilyContract(
        family="TREND_PULLBACK",
        implementation_paths=(
            "src/finam_core/research/"
            "postgresql_edge_backtest_adapter_v1.py",
        ),
        entrypoint_paths=(
            "src/finam_core/research/"
            "postgresql_edge_backtest_adapter_v1.py",
        ),
        config_paths=(),
        required_tokens=(
            "TREND_PULLBACK_V1",
            "trend_pullback_signal",
        ),
        classification="SIGNAL_FAMILY",
    ),
    FamilyContract(
        family="RELATIVE_STRENGTH",
        implementation_paths=(
            "src/scripts/"
            "build_strategy_execution_runner_v1.py",
        ),
        entrypoint_paths=(
            "src/scripts/"
            "run_relative_strength_parameter_adapter_v2.py",
        ),
        config_paths=(),
        required_tokens=(
            "RELATIVE_STRENGTH_V1",
        ),
        classification="SIGNAL_FAMILY",
    ),
    FamilyContract(
        family="INTERMARKET_LEAD_LAG",
        implementation_paths=(
            "src/scripts/"
            "build_intermarket_lead_lag_engine_v1.py",
        ),
        entrypoint_paths=(
            "src/scripts/"
            "build_intermarket_lead_lag_engine_v1.py",
            "src/scripts/"
            "run_intermarket_lead_lag_parameter_adapter_v2.py",
        ),
        config_paths=(
            "config/research/"
            "intermarket_lead_lag_v1.json",
        ),
        required_tokens=(
            "INTERMARKET_LEAD_LAG",
        ),
        classification="SIGNAL_FAMILY",
    ),
    FamilyContract(
        family="REGIME",
        implementation_paths=(
            "src/finam_core/alpha/regime_layer_v2.py",
        ),
        entrypoint_paths=(),
        config_paths=(),
        required_tokens=(
            "RegimeDecision",
        ),
        classification="CONDITIONING_LAYER",
    ),
    FamilyContract(
        family="SESSION",
        implementation_paths=(
            "src/finam_core/analytics/"
            "session_edge_guard.py",
        ),
        entrypoint_paths=(),
        config_paths=(
            "config/research/"
            "session_execution_edge_v1.json",
        ),
        required_tokens=(
            "SessionEdgeDecision",
        ),
        classification="CONDITIONING_LAYER",
    ),
    FamilyContract(
        family="VOLATILITY_STATE",
        implementation_paths=(
            "src/finam_core/research/"
            "futures_mtf_regime_aggregator.py",
        ),
        entrypoint_paths=(),
        config_paths=(),
        required_tokens=(
            "volatility_state",
        ),
        classification="CONDITIONING_LAYER",
    ),
)


def path_exists(relative: str) -> bool:
    return (ROOT / relative).is_file()


def read_text(relative: str) -> str:
    path = ROOT / relative

    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def python_syntax_ok(relative: str) -> bool:
    path = ROOT / relative

    if path.suffix != ".py":
        return True

    try:
        ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            ),
            filename=str(path),
        )
    except (OSError, SyntaxError):
        return False

    return True


def token_evidence(
    contract: FamilyContract,
) -> tuple[int, list[str]]:
    searchable = (
        contract.implementation_paths
        + contract.entrypoint_paths
    )

    combined = "\n".join(
        read_text(path)
        for path in searchable
    )

    found = [
        token
        for token in contract.required_tokens
        if token in combined
    ]

    return len(found), found


def main() -> int:
    print(
        "=== UNIVERSE INDEPENDENT FAMILY "
        "RUNNABILITY AUDIT V1 ==="
    )
    print("mode=read_only_runnability_audit")
    print("family_execution_performed=0")
    print("backtest_performed=0")
    print("parameter_search_performed=0")
    print()

    runnable_signal_families = []
    conditioning_layers = []
    blocked_signal_families = []

    for contract in CONTRACTS:
        implementation_ready = all(
            path_exists(path)
            for path in contract.implementation_paths
        )

        entrypoint_ready = (
            bool(contract.entrypoint_paths)
            and all(
                path_exists(path)
                for path in contract.entrypoint_paths
            )
        )

        config_ready = (
            not contract.config_paths
            or all(
                path_exists(path)
                for path in contract.config_paths
            )
        )

        python_paths = (
            contract.implementation_paths
            + contract.entrypoint_paths
        )

        syntax_ready = all(
            python_syntax_ok(path)
            for path in python_paths
            if path_exists(path)
        )

        token_count, tokens = token_evidence(
            contract
        )

        token_ready = (
            token_count
            == len(contract.required_tokens)
        )

        if contract.classification == "SIGNAL_FAMILY":
            runnable = (
                implementation_ready
                and entrypoint_ready
                and config_ready
                and syntax_ready
                and token_ready
            )

            if runnable:
                status = "RUNNABLE_SIGNAL_FAMILY"
                runnable_signal_families.append(
                    contract.family
                )
            else:
                status = "SIGNAL_FAMILY_BLOCKED"
                blocked_signal_families.append(
                    contract.family
                )

        else:
            runnable = False
            status = "CONDITIONING_LAYER"
            conditioning_layers.append(
                contract.family
            )

        print(
            "RUNNABILITY_ROW "
            f"family={contract.family} "
            f"classification="
            f"{contract.classification} "
            f"implementation_ready="
            f"{int(implementation_ready)} "
            f"entrypoint_ready="
            f"{int(entrypoint_ready)} "
            f"config_ready="
            f"{int(config_ready)} "
            f"syntax_ready="
            f"{int(syntax_ready)} "
            f"token_ready="
            f"{int(token_ready)} "
            f"runnable_signal_family="
            f"{int(runnable)} "
            f"status={status}"
        )

        for path in contract.implementation_paths:
            print(
                "IMPLEMENTATION_ROW "
                f"family={contract.family} "
                f"path={path} "
                f"exists={int(path_exists(path))}"
            )

        for path in contract.entrypoint_paths:
            print(
                "ENTRYPOINT_ROW "
                f"family={contract.family} "
                f"path={path} "
                f"exists={int(path_exists(path))}"
            )

        for path in contract.config_paths:
            print(
                "CONFIG_ROW "
                f"family={contract.family} "
                f"path={path} "
                f"exists={int(path_exists(path))}"
            )

        print(
            "TOKEN_ROW "
            f"family={contract.family} "
            f"required={len(contract.required_tokens)} "
            f"found={token_count} "
            f"tokens="
            f"{','.join(tokens) if tokens else 'NONE'}"
        )

    print()
    print(
        "SUMMARY_ROW "
        f"families_checked={len(CONTRACTS)} "
        f"runnable_signal_families="
        f"{len(runnable_signal_families)} "
        f"conditioning_layers="
        f"{len(conditioning_layers)} "
        f"blocked_signal_families="
        f"{len(blocked_signal_families)}"
    )

    print(
        "runnable_signal_family_names="
        + (
            ",".join(runnable_signal_families)
            if runnable_signal_families
            else "NONE"
        )
    )

    print(
        "conditioning_layer_names="
        + (
            ",".join(conditioning_layers)
            if conditioning_layers
            else "NONE"
        )
    )

    print(
        "blocked_signal_family_names="
        + (
            ",".join(blocked_signal_families)
            if blocked_signal_families
            else "NONE"
        )
    )

    print("family_execution_performed=0")
    print("backtest_performed=0")
    print("parameter_search_performed=0")
    print("economic_edge_claimed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "UNIVERSE_INDEPENDENT_FAMILY_"
        "RUNNABILITY_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
