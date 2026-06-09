#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

DDL = """
CREATE TABLE IF NOT EXISTS runtime_contract_governor_snapshot (
    id BIGSERIAL PRIMARY KEY,
    snapshot_ts timestamptz NOT NULL DEFAULT now(),
    root_symbol text NOT NULL,
    runtime_symbol text,
    calendar_current text,
    calendar_next text,
    selector_liquidity text,
    days_to_current_last_trade integer,
    decision text,
    severity text,
    action text,
    reason text,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_contract_governor_snapshot_ts
ON runtime_contract_governor_snapshot(snapshot_ts);

CREATE INDEX IF NOT EXISTS idx_runtime_contract_governor_snapshot_root
ON runtime_contract_governor_snapshot(root_symbol);
"""

INSERT_SQL = """
INSERT INTO runtime_contract_governor_snapshot (
    root_symbol,
    runtime_symbol,
    calendar_current,
    calendar_next,
    selector_liquidity,
    days_to_current_last_trade,
    decision,
    severity,
    action,
    reason,
    raw_json
)
VALUES (
    %(root)s,
    %(runtime_symbol)s,
    %(calendar_current)s,
    %(calendar_next)s,
    %(selector_liquidity)s,
    %(days_to_current_last_trade)s,
    %(decision)s,
    %(severity)s,
    %(action)s,
    %(reason)s,
    %(raw_json)s
);
"""

def parse_fields(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in line.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        out[key] = value
    return out

def to_int_or_none(value: str | None):
    if value in (None, "", "None"):
        return None
    try:
        return int(value)
    except Exception:
        return None

def main() -> None:
    print("=== RUNTIME CONTRACT GOVERNOR SNAPSHOT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    proc = subprocess.run(
        ["python", "src/scripts/analytics/build_runtime_contract_governor_advisory_v1.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    if proc.returncode != 0:
        print("SNAPSHOT_ROWS")
        print("NONE")
        print()
        print("SNAPSHOTS_WRITTEN=0")
        print("VERDICT=GOVERNOR_ADVISORY_FAILED")
        print("RUNTIME_CONTRACT_GOVERNOR_SNAPSHOT_V1_OK")
        return

    rows = []
    for line in proc.stdout.splitlines():
        if line.startswith("GOVERNOR_ROW "):
            rows.append(parse_fields(line))

    written = 0

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)

            print("SNAPSHOT_ROWS")

            for row in rows:
                payload = {
                    "root": row.get("root"),
                    "runtime_symbol": row.get("runtime_symbol"),
                    "calendar_current": row.get("calendar_current"),
                    "calendar_next": row.get("calendar_next"),
                    "selector_liquidity": row.get("selector_liquidity"),
                    "days_to_current_last_trade": to_int_or_none(row.get("days_to_current_last_trade")),
                    "decision": row.get("decision"),
                    "severity": row.get("severity"),
                    "action": row.get("action"),
                    "reason": row.get("reason"),
                    "raw_json": json.dumps(row, ensure_ascii=False),
                }

                cur.execute(INSERT_SQL, payload)
                written += 1

                print(
                    "SNAPSHOT_ROW "
                    f"root={payload['root']} "
                    f"runtime_symbol={payload['runtime_symbol']} "
                    f"severity={payload['severity']} "
                    f"decision={payload['decision']} "
                    f"action={payload['action']} "
                    f"reason={payload['reason']}"
                )

            conn.commit()

    print()
    print(f"SNAPSHOTS_WRITTEN={written}")
    print("VERDICT=SNAPSHOT_RECORDED")
    print("RUNTIME_CONTRACT_GOVERNOR_SNAPSHOT_V1_OK")

if __name__ == "__main__":
    main()
