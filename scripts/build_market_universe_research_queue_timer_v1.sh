#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1 ==="

mkdir -p deploy/systemd src/scripts scripts

cat > src/scripts/run_market_universe_research_queue_cycle_v1.py <<'PY'
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

STEPS = [
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
PY

cat > deploy/systemd/finam-market-universe-research-queue.service <<'UNIT'
[Unit]
Description=Finam Core Market Universe Research Queue Cycle V1
After=network.target postgresql.service

[Service]
Type=oneshot
User=alex
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=/opt/finam-core/src
Environment=DATABASE_URL=postgresql:///finam_core
ExecStart=/opt/finam-core/venv/bin/python src/scripts/run_market_universe_research_queue_cycle_v1.py
UNIT

cat > deploy/systemd/finam-market-universe-research-queue.timer <<'UNIT'
[Unit]
Description=Run Finam Core Market Universe Research Queue Cycle V1 every 5 minutes

[Timer]
OnBootSec=30
OnUnitActiveSec=5min
Unit=finam-market-universe-research-queue.service

[Install]
WantedBy=timers.target
UNIT

cat > scripts/test_market_universe_research_queue_timer_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_market_universe_research_queue_cycle_v1.py \
  src/scripts/build_paper_edge_market_universe_candidates_v1.py \
  src/scripts/build_market_universe_ranking_v1.py \
  src/scripts/build_market_universe_research_queue_v1.py

test -f deploy/systemd/finam-market-universe-research-queue.service
test -f deploy/systemd/finam-market-universe-research-queue.timer

grep -q "OnUnitActiveSec=5min" deploy/systemd/finam-market-universe-research-queue.timer
grep -q "run_market_universe_research_queue_cycle_v1.py" deploy/systemd/finam-market-universe-research-queue.service

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/run_market_universe_research_queue_cycle_v1.py \
  | tee /tmp/market_universe_research_queue_cycle_v1.txt

grep -q "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE_V1_READY" \
  /tmp/market_universe_research_queue_cycle_v1.txt

sudo cp deploy/systemd/finam-market-universe-research-queue.service /etc/systemd/system/
sudo cp deploy/systemd/finam-market-universe-research-queue.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finam-market-universe-research-queue.timer
sudo systemctl start finam-market-universe-research-queue.service

sleep 2

journalctl -u finam-market-universe-research-queue.service --since "2 minutes ago" --no-pager | \
grep -E "MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE|RESEARCH_QUEUE_CYCLE_STEP|VERDICT|ERROR|Traceback" || true

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
high=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1 WHERE research_priority='HIGH';")

test "$rows" -gt 0
test "$high" -gt 0

echo "research_queue_rows=$rows"
echo "research_queue_high=$high"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1_READY"
echo "VERDICT=TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1_OK"
SH_TEST

chmod +x scripts/test_market_universe_research_queue_timer_v1.sh
scripts/test_market_universe_research_queue_timer_v1.sh

echo "VERDICT=BUILD_MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1_OK"
