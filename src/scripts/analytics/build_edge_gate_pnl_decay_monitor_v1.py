from __future__ import annotations

import json
from pathlib import Path


STATE_PATH = Path("runtime/edge_gate_decay_state_v1.json")


def main() -> int:
    state = json.loads(
        STATE_PATH.read_text(encoding="utf-8")
    )

    runtime_state = dict(
        state.get("runtime_state", {})
    )

    print("EDGE_GATE_PNL_DECAY_MONITOR_V1", flush=True)

    print(
        "EDGE_GATE_PNL_DECAY_MONITOR_STATUS",
        f"enabled={state.get('enabled')}",
        f"windows={len(runtime_state)}",
        f"global_expectancy_floor={state.get('global_expectancy_floor')}",
        flush=True,
    )

    for key, value in sorted(runtime_state.items()):
        expectancy = float(
            value.get("expectancy_points", 0.0)
        )

        pnl = float(
            value.get("pnl_points", 0.0)
        )

        closed = int(
            value.get("closed_trades", 0)
        )

        decay_state = (
            "DECAY"
            if expectancy <= 0
            else "HEALTHY"
        )

        print(
            "EDGE_GATE_PNL_DECAY_ROW",
            f"key={key}",
            f"expectancy_points={expectancy}",
            f"pnl_points={pnl}",
            f"closed_trades={closed}",
            f"decay_state={decay_state}",
            flush=True,
        )

    print(
        "EDGE_GATE_PNL_DECAY_MONITOR_V1_OK",
        f"windows={len(runtime_state)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
