from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime

SPRINT_NAME = os.getenv("EDGE_SPRINT_NAME", "EDGE_SPRINT")
ROOT = os.getcwd()

STAGES = [
    ("PARAMETER_SEARCH", "scripts/build_parameter_search_grid_v1.sh"),
    ("EDGE_LAB", "scripts/build_edge_lab_foundation_v1.sh"),
    ("EXECUTION", "scripts/build_strategy_execution_runner_v1.sh"),
    ("EDGE_SCORE", "scripts/build_edge_score_engine_v2.sh"),
    ("AUDIT", "scripts/build_edge_pipeline_audit_v1.sh"),
]

def run_stage(name: str, script: str) -> None:
    print(f"\n===== {name} =====")
    subprocess.run(["bash", script], check=True, cwd=ROOT)

def main() -> None:
    started = datetime.now(UTC)

    print("=== EDGE_SPRINT_ENGINE_V1 ===")
    print(f"sprint={SPRINT_NAME}")
    print(f"started={started.isoformat()}")

    for name, script in STAGES:
        run_stage(name, script)

    finished = datetime.now(UTC)

    print(f"finished={finished.isoformat()}")
    print("status=DONE")
    print("VERDICT=EDGE_SPRINT_ENGINE_V1_READY")

if __name__ == "__main__":
    main()
