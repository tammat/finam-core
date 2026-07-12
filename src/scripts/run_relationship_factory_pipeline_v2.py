from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
PYTHON = str(ROOT / ".venv/bin/python")
TARGETS = ["SBER@MISX", "LKOH@MISX", "GAZP@MISX", "PLZL@MISX"]


def run(script: str, *args: str, timeout: int = 300) -> None:
    env = dict(os.environ, DATABASE_URL=DB, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([PYTHON, script, *args], cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout, check=False)
    print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(f"PIPELINE_STEP_FAILED script={script} code={result.returncode} stderr={result.stderr[-1000:]}")


def market_ready_targets() -> list[str]:
    ready: list[str] = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            for symbol in TARGETS:
                cur.execute("""SELECT market_data_status FROM analytics.relationship_data_quality_gate_v1
                    WHERE symbol=%s AND timeframe='M5' ORDER BY created_at DESC LIMIT 1""", (symbol,))
                row = cur.fetchone()
                if row and row[0] == "READY":
                    ready.append(symbol)
    return ready


def main() -> None:
    run("src/scripts/build_relationship_data_quality_gate_v1.py")
    targets = market_ready_targets()
    if targets:
        run("src/scripts/build_historical_regime_snapshots_v2.py", "--symbols", ",".join(targets), timeout=600)
    run("src/scripts/build_relationship_data_quality_gate_v1.py")
    run("src/scripts/build_relationship_factory_v2.py", timeout=600)
    print(f"market_ready_targets={len(targets)}")
    print("promotion_allowed=0")
    print("VERDICT=RELATIONSHIP_FACTORY_PIPELINE_V2_OK")


if __name__ == "__main__":
    main()
