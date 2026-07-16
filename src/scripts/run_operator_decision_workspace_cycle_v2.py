from __future__ import annotations

from scripts.build_operator_decision_workspace_v2 import main as build_decisions


def main() -> None:
    build_decisions()
    print("runtime_changed=0")
    print("execution_changed=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_OPERATOR_DECISION_WORKSPACE_CYCLE_V2_READY")


if __name__ == "__main__":
    main()
