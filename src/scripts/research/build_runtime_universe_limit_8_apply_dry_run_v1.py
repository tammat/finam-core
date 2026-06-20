#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import psycopg2
import psycopg2.extras

TARGET_LIMIT = 8
ENV_KEYS = ["RUNTIME_ACTIVE_UNIVERSE_LIMIT", "RUNTIME_MAX_SYMBOLS"]

def systemd_env_probe(unit: str) -> dict:
    try:
        p = subprocess.run(
            ["systemctl", "show", unit, "-p", "Environment", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "unit": unit,
            "returncode": p.returncode,
            "environment_line": p.stdout.strip(),
            "stderr": p.stderr.strip(),
        }
    except Exception as exc:
        return {"unit": unit, "error": str(exc)}

def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    runtime_env = {k: os.getenv(k) for k in ENV_KEYS}

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select symbol, strategy, score::numeric as score, priority, source
                from dynamic_watchlist
                where symbol like '%@MISX'
                order by priority desc nulls last, score desc nulls last, symbol
            """)
            dyn = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                select symbol, strategy, score, priority, is_enabled, source, updated_at
                from runtime_active_universe
                where symbol like '%@MISX'
                order by is_enabled desc, priority desc nulls last, score desc nulls last, symbol
            """)
            runtime = [dict(r) for r in cur.fetchall()]

    current_selected = [r for r in runtime if r.get("is_enabled")]
    planned_selected = dyn[:TARGET_LIMIT]
    current_symbols = {r["symbol"] for r in current_selected}
    planned_symbols = {r["symbol"] for r in planned_selected}

    out = {
        "verdict": "RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_READY",
        "mode": "dry_run",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "target_limit": TARGET_LIMIT,
        "env_required": {
            "RUNTIME_ACTIVE_UNIVERSE_LIMIT": str(TARGET_LIMIT),
            "RUNTIME_MAX_SYMBOLS": str(TARGET_LIMIT),
        },
        "current_process_env": runtime_env,
        "systemd_env": [
            systemd_env_probe("finam-runtime-governance.service"),
            systemd_env_probe("finam-paper-pipeline.service"),
        ],
        "current_active_symbols": sorted(current_symbols),
        "planned_limit_8_symbols": [r["symbol"] for r in planned_selected],
        "would_add": sorted(planned_symbols - current_symbols),
        "would_remove": sorted(current_symbols - planned_symbols),
        "selected_at_8": planned_selected,
        "safety": {
            "do_not_edit_code_defaults": True,
            "do_not_enable_execution": True,
            "do_not_enable_real_trading": True,
            "rollback_env": {
                "RUNTIME_ACTIVE_UNIVERSE_LIMIT": "5",
                "RUNTIME_MAX_SYMBOLS": "5",
            },
        },
        "manual_apply_commands": [
            "sudo systemctl edit finam-runtime-governance.service",
            "set Environment=RUNTIME_ACTIVE_UNIVERSE_LIMIT=8 RUNTIME_MAX_SYMBOLS=8",
            "sudo systemctl daemon-reload",
            "sudo systemctl restart finam-runtime-governance.service",
            "sudo systemctl restart finam-paper-pipeline.service",
        ],
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print("VERDICT=RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_READY")
    print("TEST_RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
