from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[2]
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
PYTHON = os.getenv("MARKETCORE_PYTHON", str(ROOT / ".venv/bin/python"))
MIN_BARS = 6000
MIN_REGIME_COVERAGE = 0.80


def run(script: str, *args: str, timeout: int = 900) -> None:
    env = dict(
        os.environ,
        DATABASE_URL=DB,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [PYTHON, script, *args], cwd=ROOT, env=env, text=True,
        capture_output=True, timeout=timeout, check=False,
    )
    print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(
            f"PIPELINE_STEP_FAILED script={script} code={result.returncode} "
            f"stderr={result.stderr[-1200:]}"
        )


def regime_targets() -> list[str]:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH latest AS (
                    SELECT audit_run_id
                    FROM analytics.relationship_data_quality_gate_v1
                    ORDER BY created_at DESC LIMIT 1
                )
                SELECT symbol
                FROM analytics.relationship_data_quality_gate_v1
                WHERE audit_run_id=(SELECT audit_run_id FROM latest)
                  AND timeframe='M5'
                  AND bars >= %s
                  AND regime_coverage_ratio < %s
                ORDER BY symbol
                """,
                (MIN_BARS, MIN_REGIME_COVERAGE),
            )
            return [str(row[0]) for row in cur.fetchall()]


def main() -> None:
    run("src/scripts/build_relationship_data_quality_gate_v1.py")
    targets = regime_targets()
    if targets:
        run(
            "src/scripts/build_historical_regime_snapshots_v2.py",
            "--symbols", ",".join(targets), timeout=1800,
        )
    run("src/scripts/build_relationship_data_quality_gate_v1.py")
    run("src/scripts/build_edge_regime_hypothesis_discovery_v2.py", timeout=1800)
    print(f"regime_targets={len(targets)}")
    print("promotion_allowed=0")
    print("VERDICT=EDGE_HYPOTHESIS_PIPELINE_V1_OK")


if __name__ == "__main__":
    main()
