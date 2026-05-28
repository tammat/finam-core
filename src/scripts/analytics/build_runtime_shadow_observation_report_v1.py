from __future__ import annotations

import json
import subprocess
from pathlib import Path


DECAY_STATE_PATH = Path("runtime/edge_gate_decay_state_v1.json")


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def main() -> int:
    state = json.loads(
        DECAY_STATE_PATH.read_text(encoding="utf-8")
    )

    runtime_state = dict(
        state.get("runtime_state", {}) or {}
    )

    total_windows = len(runtime_state)
    healthy_windows = 0
    decay_windows = 0
    shadow_block_candidates = 0

    print("RUNTIME_SHADOW_OBSERVATION_REPORT_V1", flush=True)

    for key, value in sorted(runtime_state.items()):
        expectancy = float(value.get("expectancy_points", 0.0) or 0.0)
        pnl = float(value.get("pnl_points", 0.0) or 0.0)
        closed = int(value.get("closed_trades", 0) or 0)

        decay_state = "DECAY" if expectancy <= 0 else "HEALTHY"
        shadow_candidate = expectancy <= 0 and closed >= 30

        if decay_state == "HEALTHY":
            healthy_windows += 1
        else:
            decay_windows += 1

        if shadow_candidate:
            shadow_block_candidates += 1

        print(
            "RUNTIME_SHADOW_OBSERVATION_ROW",
            f"key={key}",
            f"expectancy_points={expectancy}",
            f"pnl_points={pnl}",
            f"closed_trades={closed}",
            f"decay_state={decay_state}",
            f"shadow_block_candidate={shadow_candidate}",
            flush=True,
        )

    if total_windows == 0:
        status = "SHADOW_EMPTY"
    elif decay_windows <= healthy_windows:
        status = "SHADOW_STABLE"
    else:
        status = "SHADOW_DECAY_RISK"

    if not git_clean():
        status = "WARN_GIT_DIRTY"

    print(
        "RUNTIME_SHADOW_OBSERVATION_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"total_windows={total_windows}",
        f"healthy_windows={healthy_windows}",
        f"decay_windows={decay_windows}",
        f"shadow_block_candidates={shadow_block_candidates}",
        flush=True,
    )

    print(
        "RUNTIME_SHADOW_OBSERVATION_REPORT_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
