from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

STEPS = [
    (
        "db_job_scheduler",
        "src/scripts/run_db_job_scheduler_v1.py",
        "VERDICT=DB_JOB_SCHEDULER_",
    ),
    (
        "market_universe_candidates",
        "src/scripts/build_paper_edge_market_universe_candidates_v1.py",
        "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_READY",
    ),
    (
        "market_universe_ranking",
        "src/scripts/build_market_universe_ranking_v1.py",
        "VERDICT=MARKET_UNIVERSE_RANKING_V1_READY",
    ),
    (
        "market_universe_research_queue",
        "src/scripts/build_market_universe_research_queue_v1.py",
        "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_V1_READY",
    ),
]


def admission_decision(now: datetime | None = None) -> tuple[bool, str]:
    local = (now or datetime.now(ZoneInfo("Europe/Moscow"))).astimezone(
        ZoneInfo("Europe/Moscow")
    )
    minute = local.hour * 60 + local.minute
    if local.weekday() < 5 and 6 * 60 + 40 <= minute < 7 * 60 + 20:
        return False, "MARKET_OPEN_BLACKOUT_0640_0720_MSK"
    load_1m = os.getloadavg()[0]
    limit = max(1.0, float(os.getenv("MARKET_UNIVERSE_QUEUE_MAX_LOAD_1M", "3.0")))
    if load_1m >= limit:
        return False, f"RESOURCE_GATE_LOAD_HIGH:{load_1m:.2f}>={limit:.2f}"
    return True, "HEADROOM_AVAILABLE"


def run_step(name: str, script: str, expected: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("DATABASE_URL", DB)

    started = time.monotonic()
    print(f"RESEARCH_QUEUE_CYCLE_STEP_START name={name} script={script}", flush=True)

    result = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)

    elapsed_ms = int((time.monotonic() - started) * 1000)

    if result.returncode != 0:
        raise RuntimeError(f"step_failed name={name} rc={result.returncode}")

    if expected not in result.stdout:
        raise RuntimeError(f"expected_verdict_missing name={name} expected={expected}")

    print(f"RESEARCH_QUEUE_CYCLE_STEP_DONE name={name} elapsed_ms={elapsed_ms}", flush=True)


def main() -> None:
    started = time.monotonic()
    print("=== MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE_V1 ===", flush=True)

    allowed, reason = admission_decision()
    if not allowed:
        print(f"RESEARCH_QUEUE_CYCLE_DEFERRED reason={reason}", flush=True)
        print("runtime_changed=0")
        print("execution_changed=0")
        print("VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE_V1_DEFERRED")
        return

    for name, script, expected in STEPS:
        run_step(name, script, expected)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    print(f"total_elapsed_ms={elapsed_ms}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE_V1_READY")


if __name__ == "__main__":
    main()
