from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SHADOW_EXPERIMENT_GUARD_V1"
POLICY_CODE = "ATR_TRAIL_14_2_5"
NAMESPACE = uuid.UUID("67b5ebf6-87d4-4f88-8a27-07d7a3698dbe")
ROOT = Path("/opt/finam-core")
WORKER_LOG = ROOT / "data/logs/forward_edge_observation_worker_v1.log"
WS_LOG = ROOT / "data/logs/finam_microstructure_ws_v1.log"

CRITERIA = {
    "minimum_closed_shadow_trades": 100,
    "minimum_trading_sessions": 10,
    "minimum_net_profit_factor": 1.0,
    "minimum_net_expectancy": 0.0,
    "maximum_unsafe_rows": 0,
    "comparison_required": "FIXED_HOLD_VS_ATR_TRAIL",
    "regime_concentration_check_required": True,
    "instrument_concentration_check_required": True,
    "promotion_automatic": False,
}

FROZEN_POLICY = {
    "baseline": "FIXED_HOLD",
    "trailing": POLICY_CODE,
    "atr_lookback": 14,
    "atr_multiplier": 2.5,
    "commission_bps": 8.0,
    "spread_status": "UNVERIFIED_UNTIL_BID_ASK",
    "slippage_status": "UNVERIFIED_UNTIL_BID_ASK",
    "historical_backfill_allowed": False,
    "broker_orders_allowed": False,
    "runtime_allowed": False,
    "execution_enabled": False,
}

DDL = """
CREATE TABLE IF NOT EXISTS analytics.shadow_experiment_guard_v1 (
    experiment_id uuid PRIMARY KEY,
    cohort_id uuid NOT NULL,
    policy_code text NOT NULL,
    criteria_json jsonb NOT NULL,
    frozen_policy_json jsonb NOT NULL,
    guard_status text NOT NULL,
    source_version text NOT NULL,
    frozen_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(cohort_id,policy_code)
);
CREATE TABLE IF NOT EXISTS analytics.shadow_experiment_guard_check_v1 (
    guard_check_id bigserial PRIMARY KEY,
    experiment_id uuid NOT NULL REFERENCES analytics.shadow_experiment_guard_v1(experiment_id),
    check_status text NOT NULL,
    candidates integer NOT NULL,
    observations integer NOT NULL,
    shadow_total integer NOT NULL,
    trailing_total integer NOT NULL,
    unsafe_rows integer NOT NULL,
    cron_ready boolean NOT NULL,
    worker_log_ready boolean NOT NULL,
    websocket_connected boolean NOT NULL,
    disk_used_pct numeric NOT NULL,
    memory_available_mb numeric NOT NULL,
    reasons_json jsonb NOT NULL,
    evidence_json jsonb NOT NULL,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_shadow_experiment_guard_check_v1_time
ON analytics.shadow_experiment_guard_check_v1(experiment_id,created_at DESC);
"""


def command_ok(args: list[str], contains: str = "") -> bool:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    return result.returncode == 0 and (not contains or contains in result.stdout)


def log_contains(path: Path, token: str) -> bool:
    if not path.exists():
        return False
    return token in path.read_text(encoding="utf-8", errors="replace")[-12000:]


def memory_available_mb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return float(line.split()[1]) / 1024
    return 0.0


def main() -> int:
    cron_ready = command_ok(["crontab", "-l"], "run-forward-edge-observation-worker-v1.sh")
    worker_log_ready = log_contains(WORKER_LOG, "VERDICT=FORWARD_EDGE_SHADOW_TRAILING_V1_OK")
    websocket_connected = command_ok(["pgrep", "-f", "run_finam_microstructure_ws_v1.py"]) and log_contains(WS_LOG, "status=CONNECTED")
    disk = shutil.disk_usage(ROOT)
    disk_used_pct = 100.0 * disk.used / disk.total
    memory_mb = memory_available_mb()

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                print("VERDICT=SHADOW_EXPERIMENT_GUARD_V1_NO_COHORT")
                return 1
            cohort_id = latest["cohort_id"]
            experiment_id = uuid.uuid5(NAMESPACE, f"{cohort_id}:{POLICY_CODE}")
            cur.execute("""
                INSERT INTO analytics.shadow_experiment_guard_v1 (
                    experiment_id,cohort_id,policy_code,criteria_json,frozen_policy_json,guard_status,source_version
                ) VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,'ARMED',%s)
                ON CONFLICT (cohort_id,policy_code) DO NOTHING
            """, (str(experiment_id),str(cohort_id),POLICY_CODE,json.dumps(CRITERIA),json.dumps(FROZEN_POLICY),SOURCE_VERSION))
            cur.execute("SELECT criteria_json,frozen_policy_json FROM analytics.shadow_experiment_guard_v1 WHERE experiment_id=%s", (str(experiment_id),))
            frozen = cur.fetchone()
            if frozen["criteria_json"] != CRITERIA or frozen["frozen_policy_json"] != FROZEN_POLICY:
                raise RuntimeError("SHADOW_EXPERIMENT_FROZEN_CONFIGURATION_MISMATCH")

            cur.execute("SELECT count(*) candidates FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s", (cohort_id,))
            candidates = int(cur.fetchone()["candidates"])
            cur.execute("SELECT count(*) observations FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s", (cohort_id,))
            observations = int(cur.fetchone()["observations"])
            cur.execute("SELECT count(*) total,count(*) FILTER(WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe FROM analytics.forward_edge_shadow_trade_v1 WHERE cohort_id=%s", (cohort_id,))
            base = dict(cur.fetchone() or {})
            cur.execute("SELECT count(*) total,count(*) FILTER(WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe FROM analytics.forward_edge_shadow_exit_variant_v1 WHERE cohort_id=%s AND policy_code=%s", (cohort_id,POLICY_CODE))
            trailing = dict(cur.fetchone() or {})
            unsafe = int(base.get("unsafe") or 0) + int(trailing.get("unsafe") or 0)

            reasons = []
            if candidates == 0: reasons.append("NO_CANDIDATES")
            if unsafe: reasons.append("UNSAFE_SHADOW_ROWS")
            if not cron_ready: reasons.append("CRON_NOT_READY")
            if not worker_log_ready: reasons.append("WORKER_LOG_NOT_READY")
            if not websocket_connected: reasons.append("WEBSOCKET_NOT_CONNECTED")
            if disk_used_pct >= 85: reasons.append("DISK_CRITICAL")
            if memory_mb <= 2048: reasons.append("MEMORY_CRITICAL")
            status = "READY_FOR_SHADOW_OPEN" if not reasons else "BLOCKED"
            evidence = {
                "worker_log": str(WORKER_LOG),
                "websocket_log": str(WS_LOG),
                "paper_allowed": False,
                "live_allowed": False,
                "broker_orders_allowed": False,
            }
            cur.execute("""
                INSERT INTO analytics.shadow_experiment_guard_check_v1 (
                    experiment_id,check_status,candidates,observations,shadow_total,trailing_total,unsafe_rows,
                    cron_ready,worker_log_ready,websocket_connected,disk_used_pct,memory_available_mb,
                    reasons_json,evidence_json,source_version
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
            """, (str(experiment_id),status,candidates,observations,int(base.get("total") or 0),int(trailing.get("total") or 0),unsafe,
                  cron_ready,worker_log_ready,websocket_connected,disk_used_pct,memory_mb,json.dumps(reasons),json.dumps(evidence),SOURCE_VERSION))

    print(f"experiment_id={experiment_id}")
    print(f"cohort_id={cohort_id}")
    print(f"status={status}")
    print(f"candidates={candidates}")
    print(f"observations={observations}")
    print(f"shadow_total={int(base.get('total') or 0)}")
    print(f"trailing_total={int(trailing.get('total') or 0)}")
    print(f"unsafe={unsafe}")
    print(f"cron_ready={int(cron_ready)}")
    print(f"worker_log_ready={int(worker_log_ready)}")
    print(f"websocket_connected={int(websocket_connected)}")
    print(f"disk_used_pct={disk_used_pct:.1f}")
    print(f"memory_available_mb={memory_mb:.0f}")
    print(f"reasons={','.join(reasons) if reasons else 'NONE'}")
    print("VERDICT=SHADOW_EXPERIMENT_GUARD_V1_OK")
    return 0 if status == "READY_FOR_SHADOW_OPEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
