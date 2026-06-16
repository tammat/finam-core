#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

GENERATOR = "src/scripts/research/build_sber_d1_shadow_signal_generator_v1.py"

def main() -> int:
    print("=== SBER D1 SHADOW SCHEDULER V1 ===")
    print("mode=shadow_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    result = subprocess.run(
        [sys.executable, GENERATOR],
        capture_output=True,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(
            f"SBER_D1_SHADOW_SCHEDULER_FAILED exit_code={result.returncode}",
            flush=True,
        )
        return result.returncode

    print("SBER_D1_SHADOW_SCHEDULER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
