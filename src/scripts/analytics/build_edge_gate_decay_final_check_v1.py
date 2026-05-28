from __future__ import annotations

import json
import subprocess
from pathlib import Path


DECAY_STATE_PATH = Path("runtime/edge_gate_decay_state_v1.json")
PRODUCTION_STATUS_SCRIPT = Path("src/scripts/analytics/build_edge_gate_production_status_v1.py")
DECAY_MONITOR_SCRIPT = Path("src/scripts/analytics/build_edge_gate_pnl_decay_monitor_v1.py")


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def py_compile_ok() -> bool:
    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            "src/finam_core/analytics/edge_gate_pnl_decay_monitor_v1.py",
            "src/scripts/analytics/build_edge_gate_pnl_decay_monitor_v1.py",
            "src/scripts/analytics/build_edge_gate_production_status_v1.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def run_script(path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["python", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0, result.stdout + result.stderr


def main() -> int:
    state = json.loads(DECAY_STATE_PATH.read_text(encoding="utf-8"))
    runtime_state = dict(state.get("runtime_state", {}) or {})

    healthy = 0
    decay = 0

    for value in runtime_state.values():
        expectancy = float(value.get("expectancy_points", 0.0) or 0.0)
        if expectancy > 0:
            healthy += 1
        else:
            decay += 1

    clean = git_clean()
    compile_ok = py_compile_ok()

    prod_ok, prod_output = run_script(PRODUCTION_STATUS_SCRIPT)
    decay_ok, decay_output = run_script(DECAY_MONITOR_SCRIPT)

    production_ready = "status=PRODUCTION_READY" in prod_output
    decay_monitor_ok = "EDGE_GATE_PNL_DECAY_MONITOR_V1_OK" in decay_output

    status = "OK"

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_PY_COMPILE"
    elif not bool(state.get("enabled")):
        status = "FAIL_DECAY_DISABLED"
    elif not prod_ok or not production_ready:
        status = "FAIL_PRODUCTION_STATUS"
    elif not decay_ok or not decay_monitor_ok:
        status = "FAIL_DECAY_MONITOR"
    elif len(runtime_state) == 0:
        status = "WARN_EMPTY_DECAY_STATE"
    elif decay == 0:
        status = "WARN_NO_DECAY_WINDOWS"
    elif healthy == 0:
        status = "WARN_NO_HEALTHY_WINDOWS"

    print("EDGE_GATE_DECAY_FINAL_CHECK_V1", flush=True)

    print(
        "EDGE_GATE_DECAY_FINAL_CHECK_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"decay_enabled={state.get('enabled')}",
        f"runtime_windows={len(runtime_state)}",
        f"healthy_windows={healthy}",
        f"decay_windows={decay}",
        f"global_expectancy_floor={state.get('global_expectancy_floor')}",
        f"rolling_window_trades={state.get('rolling_window_trades')}",
        f"production_ready={production_ready}",
        f"decay_monitor_ok={decay_monitor_ok}",
        flush=True,
    )

    for key, value in sorted(runtime_state.items()):
        expectancy = float(value.get("expectancy_points", 0.0) or 0.0)
        decay_state = "HEALTHY" if expectancy > 0 else "DECAY"

        print(
            "EDGE_GATE_DECAY_FINAL_CHECK_ROW",
            f"key={key}",
            f"expectancy_points={expectancy}",
            f"pnl_points={value.get('pnl_points')}",
            f"closed_trades={value.get('closed_trades')}",
            f"decay_state={decay_state}",
            flush=True,
        )

    print(
        "EDGE_GATE_DECAY_FINAL_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
