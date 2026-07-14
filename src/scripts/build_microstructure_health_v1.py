from __future__ import annotations

import json
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "runtime" / "microstructure_health_policy_v1.json"
SOURCE_VERSION = "MICROSTRUCTURE_HEALTH_V1"

DDL = """
CREATE TABLE IF NOT EXISTS analytics.microstructure_health_v1 (
    symbol text PRIMARY KEY,
    session_open boolean NOT NULL,
    last_observed_at timestamptz,
    last_exchange_ts timestamptz,
    observed_age_seconds numeric,
    exchange_age_seconds numeric,
    snapshots_in_window integer NOT NULL,
    max_gap_seconds numeric,
    health_status text NOT NULL CHECK (health_status IN ('FRESH','STALE','NO_DATA','OFF_SESSION')),
    signal_allowed boolean NOT NULL DEFAULT false,
    reasons_json jsonb NOT NULL,
    policy_version text NOT NULL,
    source_version text NOT NULL,
    refreshed_at timestamptz NOT NULL DEFAULT now()
);
"""


def session_is_open(now: datetime, policy: dict) -> bool:
    local = now.astimezone(ZoneInfo(policy["session_timezone"]))
    start = time.fromisoformat(policy["session_start"])
    end = time.fromisoformat(policy["session_end"])
    return local.weekday() < 5 and start <= local.time().replace(tzinfo=None) <= end


def main() -> int:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute("SELECT now() AS now")
            now = cur.fetchone()["now"]
            is_open = session_is_open(now, policy)
            fresh = stale = no_data = off_session = 0
            for symbol in policy["symbols"]:
                cur.execute("""
                    WITH recent AS (
                        SELECT observed_at,lag(observed_at) OVER (ORDER BY observed_at) AS previous_at
                        FROM analytics.market_microstructure_snapshot_v1
                        WHERE symbol=%s AND observed_at>=now()-(%s::text || ' minutes')::interval
                    ), latest AS (
                        SELECT max(observed_at) AS last_observed_at,max(exchange_ts) AS last_exchange_ts
                        FROM analytics.market_microstructure_snapshot_v1 WHERE symbol=%s
                    )
                    SELECT latest.*,
                           EXTRACT(EPOCH FROM (now()-last_observed_at)) AS observed_age_seconds,
                           EXTRACT(EPOCH FROM (now()-last_exchange_ts)) AS exchange_age_seconds,
                           count(recent.observed_at)::integer AS snapshots_in_window,
                           max(EXTRACT(EPOCH FROM (recent.observed_at-recent.previous_at))) AS max_gap_seconds
                    FROM latest LEFT JOIN recent ON true
                    GROUP BY latest.last_observed_at,latest.last_exchange_ts
                """, (symbol, policy["window_minutes"], symbol))
                row = dict(cur.fetchone())
                reasons: list[str] = []
                if not is_open:
                    status = "OFF_SESSION"
                    off_session += 1
                elif row["last_observed_at"] is None:
                    status = "NO_DATA"
                    reasons.append("NO_SNAPSHOTS")
                    no_data += 1
                else:
                    if float(row["observed_age_seconds"] or 1e12) > policy["maximum_observed_age_seconds"]:
                        reasons.append("OBSERVED_DATA_STALE")
                    if float(row["exchange_age_seconds"] or 1e12) > policy["maximum_exchange_age_seconds"]:
                        reasons.append("EXCHANGE_DATA_STALE")
                    if int(row["snapshots_in_window"] or 0) < policy["minimum_snapshots_in_window"]:
                        reasons.append("INSUFFICIENT_SNAPSHOTS")
                    if row["max_gap_seconds"] is not None and float(row["max_gap_seconds"]) > policy["maximum_gap_seconds"]:
                        reasons.append("SNAPSHOT_GAP_EXCEEDED")
                    status = "STALE" if reasons else "FRESH"
                    stale += int(bool(reasons))
                    fresh += int(not reasons)
                signal_allowed = is_open and status == "FRESH"
                cur.execute("""
                    INSERT INTO analytics.microstructure_health_v1 (
                        symbol,session_open,last_observed_at,last_exchange_ts,observed_age_seconds,
                        exchange_age_seconds,snapshots_in_window,max_gap_seconds,health_status,
                        signal_allowed,reasons_json,policy_version,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT(symbol) DO UPDATE SET
                        session_open=excluded.session_open,last_observed_at=excluded.last_observed_at,
                        last_exchange_ts=excluded.last_exchange_ts,observed_age_seconds=excluded.observed_age_seconds,
                        exchange_age_seconds=excluded.exchange_age_seconds,snapshots_in_window=excluded.snapshots_in_window,
                        max_gap_seconds=excluded.max_gap_seconds,health_status=excluded.health_status,
                        signal_allowed=excluded.signal_allowed,reasons_json=excluded.reasons_json,
                        policy_version=excluded.policy_version,source_version=excluded.source_version,refreshed_at=now()
                """, (
                    symbol,is_open,row["last_observed_at"],row["last_exchange_ts"],row["observed_age_seconds"],
                    row["exchange_age_seconds"],row["snapshots_in_window"],row["max_gap_seconds"],status,
                    signal_allowed,json.dumps(reasons),policy["contract_version"],SOURCE_VERSION,
                ))

    print(f"symbols={len(policy['symbols'])}")
    print(f"session_open={int(is_open)}")
    print(f"fresh={fresh}")
    print(f"stale={stale}")
    print(f"no_data={no_data}")
    print(f"off_session={off_session}")
    print(f"signal_allowed={int(is_open and stale == 0 and no_data == 0)}")
    print("VERDICT=MICROSTRUCTURE_HEALTH_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
