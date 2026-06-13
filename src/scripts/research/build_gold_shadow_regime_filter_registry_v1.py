#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"

SQL_UPDATE = """
UPDATE runtime_candidate_registry
SET
    reason='gold_runtime_watch_mode_active_with_regime_filter',
    raw_json = COALESCE(raw_json, '{}'::jsonb) || %s::jsonb,
    runtime_allowed=false,
    execution_enabled=false,
    updated_at=now()
WHERE symbol=%s
  AND status='WATCH_RUNTIME_ACTIVE'
RETURNING symbol, status, reason, runtime_allowed, execution_enabled, raw_json, updated_at;
"""

def main() -> int:
    print("=== GOLD SHADOW REGIME FILTER REGISTRY V1 ===")
    print("mode=registry_update")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    payload = {
        "mandatory_filters": {
            "gold_shadow_regime_filter_v1": {
                "enabled": True,
                "rule": "up_impulse_sell_block",
                "condition": "SELL blocked when day_move > 0 and day_range >= 100 and entry_price < last_close",
                "backtest_verdict": "GOLD_REGIME_FILTER_BACKTEST_STRONG",
                "blocked_trades": 10,
                "pnl_improvement": 1301.8,
                "runtime_allowed": False,
                "execution_enabled": False,
            }
        },
        "source": "gold_shadow_regime_filter_registry_v1",
    }

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_UPDATE, (json.dumps(payload, ensure_ascii=False), SYMBOL))
            row = cur.fetchone()

            if not row:
                print("REGISTRY_FILTER_ERROR reason=watch_runtime_active_row_missing")
                return 1

        conn.commit()

    print(
        "REGISTRY_FILTER_ROW "
        f"symbol={row['symbol']} "
        f"status={row['status']} "
        f"reason={row['reason']} "
        f"runtime_allowed={int(row['runtime_allowed'])} "
        f"execution_enabled={int(row['execution_enabled'])} "
        "mandatory_filter=gold_shadow_regime_filter_v1 "
        "rule=up_impulse_sell_block"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=GOLD_REGIME_FILTER_REGISTERED")
    print("GOLD_SHADOW_REGIME_FILTER_REGISTRY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
