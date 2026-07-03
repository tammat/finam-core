#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1 ==="

mkdir -p deploy/systemd src/scripts scripts

cat > src/scripts/run_edge_discovery_from_market_universe_cycle_v1.py <<'PY'
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
PY

cat > deploy/systemd/finam-edge-discovery-market-universe.service <<'UNIT'
[Unit]
Description=Finam Core Edge Discovery From Market Universe Cycle V1
After=network.target postgresql.service

[Service]
Type=oneshot
User=alex
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=/opt/finam-core/src
Environment=DATABASE_URL=postgresql:///finam_core
ExecStart=/opt/finam-core/venv/bin/python src/scripts/run_edge_discovery_from_market_universe_cycle_v1.py
UNIT

cat > deploy/systemd/finam-edge-discovery-market-universe.timer <<'UNIT'
[Unit]
Description=Run Finam Core Edge Discovery From Market Universe every 5 minutes

[Timer]
OnBootSec=60
OnUnitActiveSec=5min
Unit=finam-edge-discovery-market-universe.service

[Install]
WantedBy=timers.target
UNIT

cat > scripts/test_edge_discovery_from_market_universe_timer_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_edge_discovery_from_market_universe_cycle_v1.py \
  src/scripts/build_edge_discovery_from_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/run_edge_discovery_from_market_universe_cycle_v1.py \
  | tee /tmp/edge_discovery_market_universe_cycle_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_CYCLE_V1_READY" \
  /tmp/edge_discovery_market_universe_cycle_v1.txt

sudo cp deploy/systemd/finam-edge-discovery-market-universe.service /etc/systemd/system/
sudo cp deploy/systemd/finam-edge-discovery-market-universe.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now finam-edge-discovery-market-universe.timer
sudo systemctl start finam-edge-discovery-market-universe.service

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_discovery_from_market_universe_v1;")
test "$rows" -gt 0

echo "edge_discovery_rows=$rows"
echo "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1_OK"
SH_TEST

chmod +x scripts/test_edge_discovery_from_market_universe_timer_v1.sh
scripts/test_edge_discovery_from_market_universe_timer_v1.sh

echo "VERDICT=BUILD_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_TIMER_V1_OK"
