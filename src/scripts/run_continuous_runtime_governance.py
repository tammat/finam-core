from __future__ import annotations

import argparse
import subprocess
import sys
import time


STEPS = [
    ["src/scripts/build_market_radar_candidates.py"],
    ["src/scripts/build_runtime_governance_decisions.py", "--symbol-like", "NG%@RTSX"],
    ["src/scripts/build_ng_runtime_telemetry.py"],
    ["src/scripts/build_ng_active_edge_resolver.py"],
    ["src/scripts/build_ng_live_runtime_state.py"],
    ["src/scripts/sync_runtime_active_universe_from_ng_live_state.py"],
    ["src/scripts/runtime/build_runtime_rolling_strategy_stats.py"],
    ["src/scripts/runtime/build_runtime_capital_allocator.py"],
    ["src/scripts/build_portfolio_risk_state.py"],
    ["src/scripts/collect_runtime_observations.py"],
]


def run_step(step: list[str]) -> bool:
    cmd = [sys.executable, *step]
    print("RUNTIME_GOVERNANCE_STEP_START", " ".join(cmd), flush=True)
    result = subprocess.run(cmd)
    ok = result.returncode == 0
    print(
        "RUNTIME_GOVERNANCE_STEP_DONE "
        f"ok={ok} code={result.returncode} step={step[0]}",
        flush=True,
    )
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    cycle = 0

    while True:
        cycle += 1
        print(f"RUNTIME_GOVERNANCE_CYCLE_START cycle={cycle}", flush=True)

        ok_all = True
        for step in STEPS:
            ok_all = run_step(step) and ok_all

        print(
            f"RUNTIME_GOVERNANCE_CYCLE_DONE cycle={cycle} ok={ok_all}",
            flush=True,
        )

        if args.once:
            return 0 if ok_all else 1

        time.sleep(max(5, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
