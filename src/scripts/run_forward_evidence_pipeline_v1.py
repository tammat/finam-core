from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "venv/bin/python"
STEPS = (
    "src/scripts/run_forward_edge_observation_worker_v1.py",
    "src/scripts/run_forward_edge_relation_router_v1.py",
    "src/scripts/project_forward_edge_shadow_trailing_v1.py",
    "src/scripts/build_forward_edge_regime_attribution_v1.py",
    "src/scripts/build_forward_edge_regime_promotion_gate_v1.py",
    "src/scripts/build_forward_edge_loss_decomposition_v1.py",
)


def main() -> int:
    env = os.environ.copy()
    env.update({"RUNTIME_ALLOW_TRADING": "0", "EXECUTION_ENABLED": "0", "REAL_TRADING_ENABLED": "0"})
    for step in STEPS:
        result = subprocess.run([str(PYTHON), step], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
        print(f"step={step} return_code={result.returncode}")
        if result.stdout:
            print(result.stdout[-2000:])
        if result.returncode:
            if result.stderr:
                print(result.stderr[-2000:])
            raise RuntimeError(f"FORWARD_EVIDENCE_STEP_FAILED:{step}")
    print("VERDICT=FORWARD_EVIDENCE_PIPELINE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
