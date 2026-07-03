from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STEPS = [
    "src/scripts/build_paper_edge_market_data_binding_v1.py",
    "src/scripts/build_paper_edge_market_data_freshness_v1.py",
    "src/scripts/build_edge_discovery_from_market_universe_v1.py",
]

def main() -> None:
    print("=== EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_CYCLE_V1 ===", flush=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("DATABASE_URL", "postgresql:///finam_core")

    for script in STEPS:
        print(f"EDGE_DISCOVERY_STEP_START script={script}", flush=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
        )
        print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)
        if result.returncode != 0:
            raise SystemExit(result.returncode)
        print(f"EDGE_DISCOVERY_STEP_DONE script={script}", flush=True)

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_CYCLE_V1_READY")

if __name__ == "__main__":
    main()
