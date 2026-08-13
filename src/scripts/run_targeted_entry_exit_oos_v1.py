"""Targeted research executor для Entry/Exit OOS.

Использует существующий entry/exit optimizer исключительно в режиме
ENTRY_EXIT_TARGETED_RESEARCH_ONLY=1.

Торговый execution этот adapter не вызывает.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

OPTIMIZER = (
    PROJECT_ROOT
    / "src/scripts/analytics/build_entry_exit_optimizer_v1.py"
)

EXPECTED_VERDICT = (
    "VERDICT=ENTRY_EXIT_TARGETED_RESEARCH_ONLY_V1_READY"
)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"TARGETED_ENTRY_EXIT_OOS_REQUIRES_{name}"
        )

    return value


def main() -> int:
    symbol = _required_env("EDGE_SEARCH_TARGET_SYMBOL")
    strategy = _required_env("EDGE_SEARCH_TARGET_STRATEGY")
    side = _required_env("EDGE_SEARCH_TARGET_SIDE").upper()
    variant_budget_raw = os.getenv(
        "EDGE_SEARCH_TARGET_VARIANT_BUDGET", ""
    ).strip()

    variant_budget = None

    if variant_budget_raw:
        variant_budget = int(variant_budget_raw)

        if variant_budget <= 0:
            raise RuntimeError(
                "EDGE_SEARCH_TARGET_VARIANT_BUDGET_INVALID"
            )

    cycle_budget_raw = os.getenv(
        "EDGE_SEARCH_TARGET_CYCLE_BUDGET", ""
    ).strip()

    cycle_budget = None

    if cycle_budget_raw:
        cycle_budget = int(cycle_budget_raw)

        if cycle_budget <= 0:
            raise RuntimeError(
                "EDGE_SEARCH_TARGET_CYCLE_BUDGET_INVALID"
            )

    if variant_budget is not None:
        if cycle_budget is None:
            # Legacy V1 compatibility.
            cycle_budget = 1

        if cycle_budget > variant_budget:
            raise RuntimeError(
                "EDGE_SEARCH_TARGET_CYCLE_BUDGET_EXCEEDS_VARIANT_BUDGET"
            )

    elif cycle_budget is not None:
        raise RuntimeError(
            "EDGE_SEARCH_TARGET_CYCLE_BUDGET_REQUIRES_VARIANT_BUDGET"
        )

    if "@" not in symbol:
        raise RuntimeError(
            "TARGETED_ENTRY_EXIT_OOS_REQUIRES_PHYSICAL_SYMBOL"
        )

    if side not in {"LONG", "SHORT"}:
        raise RuntimeError(
            "TARGETED_ENTRY_EXIT_OOS_REQUIRES_LONG_OR_SHORT"
        )

    if not OPTIMIZER.is_file():
        raise RuntimeError(
            f"TARGETED_ENTRY_EXIT_OOS_OPTIMIZER_NOT_FOUND:{OPTIMIZER}"
        )

    env = os.environ.copy()

    # Нельзя разрешать вызывающей стороне отключить safe research mode.
    env["ENTRY_EXIT_TARGETED_RESEARCH_ONLY"] = "1"
    env["EDGE_SEARCH_TARGET_SYMBOL"] = symbol
    env["EDGE_SEARCH_TARGET_STRATEGY"] = strategy
    env["EDGE_SEARCH_TARGET_SIDE"] = side

    if variant_budget is not None:
        env["EDGE_SEARCH_TARGET_VARIANT_BUDGET"] = str(
            variant_budget
        )

    if cycle_budget is not None:
        env["EDGE_SEARCH_TARGET_CYCLE_BUDGET"] = str(
            cycle_budget
        )

    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    print("=== TARGETED ENTRY EXIT OOS V1 ===")
    print(f"target_symbol={symbol}")
    print(f"target_strategy={strategy}")
    print(f"target_side={side}")
    print(
        "target_variant_budget="
        f"{variant_budget if variant_budget is not None else 'UNBOUNDED'}"
    )
    print(
        "target_cycle_budget="
        f"{cycle_budget if cycle_budget is not None else 'UNBOUNDED'}"
    )
    print("targeted_research_only_forced=1")

    completed = subprocess.run(
        [sys.executable, str(OPTIMIZER)],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.stdout:
        print(
            completed.stdout,
            end="" if completed.stdout.endswith("\n") else "\n",
        )

    if completed.stderr:
        print(
            completed.stderr,
            file=sys.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
        )

    if completed.returncode != 0:
        print(
            f"optimizer_returncode={completed.returncode}"
        )
        return completed.returncode

    if EXPECTED_VERDICT not in completed.stdout:
        print("ERROR=TARGETED_OPTIMIZER_VERDICT_MISSING")
        return 2

    print("optimizer_returncode=0")
    print("targeted_optimizer_verdict_confirmed=1")
    print("resource_allocation_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "TARGETED_ENTRY_EXIT_OOS_EXECUTOR_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
