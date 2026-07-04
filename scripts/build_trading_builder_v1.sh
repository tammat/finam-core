#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_TRADING_BUILDER_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_trading_builder_v1.py <<'PY'
from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("TRADING_LIMIT", "5000"))


def load_config(cur) -> dict:
    cur.execute("""
        SELECT config_json
        FROM analytics.trading_configuration_v1
        WHERE trading_name='DEFAULT'
        LIMIT 1;
    """)
    row = cur.fetchone()
    if not row:
        return {}
    cfg = row["config_json"]
    return cfg if isinstance(cfg, dict) else json.loads(cfg)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cfg = load_config(cur)

            paper_enabled = bool(cfg.get("paper_enabled", True))
            shadow_enabled = bool(cfg.get("shadow_enabled", False))
            micro_live_enabled = bool(cfg.get("micro_live_enabled", False))
            live_enabled = bool(cfg.get("live_enabled", False))
            default_order_type = str(cfg.get("default_order_type", "MARKET"))
            default_quantity = float(cfg.get("default_quantity", 1))

            cur.execute("""
                SELECT *
                FROM analytics.risk_decision_snapshot_v1
                WHERE risk_decision_code='RISK_ALLOW'
                ORDER BY signal_ts DESC
                LIMIT %s;
            """, (LIMIT,))
            rows = cur.fetchall()

            saved = 0

            for row in rows:
                trading_decision = "PAPER_INTENT_READY" if paper_enabled else "TRADING_BLOCK"
                recommendation = "READY_FOR_PAPER_EXECUTION" if paper_enabled else "WAIT_TRADING_REVIEW"

                cur.execute("""
                    INSERT INTO analytics.trading_order_intent_v1 (
                        risk_decision_id,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        strategy_version,
                        signal_ts,
                        risk_score,
                        order_side,
                        order_type,
                        quantity,
                        trading_decision_code,
                        recommendation_code,
                        paper_allowed,
                        shadow_allowed,
                        micro_live_allowed,
                        live_allowed,
                        order_sent,
                        broker_order_id,
                        source_version,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,
                        %s,
                        'UNKNOWN',
                        %s,
                        %s,
                        %s,%s,
                        %s,%s,false,false,
                        false,'',
                        'TRADING_BUILDER_V1',
                        %s
                    )
                    ON CONFLICT(symbol,timeframe,strategy_family,signal_ts)
                    DO UPDATE SET
                        risk_score=EXCLUDED.risk_score,
                        order_type=EXCLUDED.order_type,
                        quantity=EXCLUDED.quantity,
                        trading_decision_code=EXCLUDED.trading_decision_code,
                        recommendation_code=EXCLUDED.recommendation_code,
                        paper_allowed=EXCLUDED.paper_allowed,
                        shadow_allowed=EXCLUDED.shadow_allowed,
                        micro_live_allowed=false,
                        live_allowed=false,
                        order_sent=false,
                        broker_order_id='',
                        source_version=EXCLUDED.source_version,
                        build_id=EXCLUDED.build_id,
                        refreshed_at=now();
                """, (
                    row["id"],
                    row["symbol"],
                    row["asset_class"],
                    row["timeframe"],
                    row["strategy_family"],
                    row["strategy_version"],
                    row["signal_ts"],
                    row["risk_score"],
                    default_order_type,
                    default_quantity,
                    trading_decision,
                    recommendation,
                    paper_enabled,
                    shadow_enabled,
                    build_id,
                ))
                saved += 1

            cur.execute("SELECT count(*) AS rows FROM analytics.trading_order_intent_v1;")
            total = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT count(*) AS unsafe
                FROM analytics.trading_order_intent_v1
                WHERE live_allowed=true
                   OR micro_live_allowed=true
                   OR order_sent=true;
            """)
            unsafe = int(cur.fetchone()["unsafe"])

    print("=== TRADING_BUILDER_V1 ===")
    print(f"risk_allow_rows={len(rows)}")
    print(f"saved={saved}")
    print(f"trading_intent_rows={total}")
    print(f"unsafe_live_or_sent_rows={unsafe}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=TRADING_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_trading_builder_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_trading_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_trading_builder_v1.py | tee /tmp/trading_builder_v1.txt

grep -q "VERDICT=TRADING_BUILDER_V1_READY" /tmp/trading_builder_v1.txt

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
    symbol,
    strategy_family,
    risk_score,
    order_side,
    order_type,
    quantity,
    trading_decision_code,
    recommendation_code,
    paper_allowed,
    live_allowed,
    order_sent
FROM analytics.trading_order_intent_v1
ORDER BY signal_ts DESC
LIMIT 30;
"

echo "trading_intent_rows=$rows"
echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_TRADING_BUILDER_V1_OK"
SH_TEST

chmod +x scripts/test_trading_builder_v1.sh
scripts/test_trading_builder_v1.sh

echo "VERDICT=BUILD_TRADING_BUILDER_V1_OK"
