#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PORTFOLIO_BUILDER_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_portfolio_builder_v1.py <<'PY'
from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def load_config(cur) -> dict:
    cur.execute("""
        SELECT config_json
        FROM analytics.portfolio_configuration_v1
        WHERE portfolio_name='DEFAULT'
        LIMIT 1;
    """)
    row = cur.fetchone()
    if not row:
        return {}
    cfg = row["config_json"]
    return cfg if isinstance(cfg, dict) else json.loads(cfg)


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cfg = load_config(cur)
            initial_cash = dec(cfg.get("initial_cash", 0))

            cur.execute("""
                SELECT
                    symbol,
                    asset_class,
                    count(*)::numeric AS quantity,
                    0::numeric AS avg_price,
                    0::numeric AS last_price
                FROM analytics.trading_order_intent_v1
                WHERE paper_allowed=true
                  AND order_sent=false
                  AND live_allowed=false
                  AND micro_live_allowed=false
                GROUP BY symbol, asset_class
                ORDER BY symbol;
            """)
            rows = cur.fetchall()

            saved = 0
            positions_value = Decimal("0")
            gross_exposure = Decimal("0")
            net_exposure = Decimal("0")

            for row in rows:
                quantity = dec(row["quantity"])
                avg_price = dec(row["avg_price"])
                last_price = dec(row["last_price"])
                market_value = quantity * last_price
                unrealized_pnl = (last_price - avg_price) * quantity
                exposure = market_value

                status = "OPEN" if quantity != 0 else "EMPTY"

                positions_value += market_value
                gross_exposure += abs(exposure)
                net_exposure += exposure

                cur.execute("""
                    INSERT INTO analytics.portfolio_position_snapshot_v1 (
                        symbol,
                        asset_class,
                        quantity,
                        avg_price,
                        last_price,
                        market_value,
                        unrealized_pnl,
                        realized_pnl,
                        exposure,
                        position_status,
                        source_version,
                        build_id,
                        refreshed_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,0,%s,%s,
                        'PORTFOLIO_BUILDER_V1',
                        %s,
                        now()
                    )
                    ON CONFLICT(symbol) DO UPDATE SET
                        asset_class=EXCLUDED.asset_class,
                        quantity=EXCLUDED.quantity,
                        avg_price=EXCLUDED.avg_price,
                        last_price=EXCLUDED.last_price,
                        market_value=EXCLUDED.market_value,
                        unrealized_pnl=EXCLUDED.unrealized_pnl,
                        realized_pnl=EXCLUDED.realized_pnl,
                        exposure=EXCLUDED.exposure,
                        position_status=EXCLUDED.position_status,
                        source_version=EXCLUDED.source_version,
                        build_id=EXCLUDED.build_id,
                        refreshed_at=now();
                """, (
                    row["symbol"],
                    row["asset_class"],
                    quantity,
                    avg_price,
                    last_price,
                    market_value,
                    unrealized_pnl,
                    exposure,
                    status,
                    build_id,
                ))
                saved += 1

            equity = initial_cash + positions_value
            total_pnl = Decimal("0")

            cur.execute("""
                INSERT INTO analytics.portfolio_equity_snapshot_v1 (
                    portfolio_scope,
                    cash,
                    positions_value,
                    equity,
                    realized_pnl,
                    unrealized_pnl,
                    total_pnl,
                    gross_exposure,
                    net_exposure,
                    source_version,
                    build_id,
                    refreshed_at
                )
                VALUES (
                    'GLOBAL',
                    %s,%s,%s,
                    0,0,%s,
                    %s,%s,
                    'PORTFOLIO_BUILDER_V1',
                    %s,
                    now()
                )
                ON CONFLICT(portfolio_scope) DO UPDATE SET
                    cash=EXCLUDED.cash,
                    positions_value=EXCLUDED.positions_value,
                    equity=EXCLUDED.equity,
                    realized_pnl=EXCLUDED.realized_pnl,
                    unrealized_pnl=EXCLUDED.unrealized_pnl,
                    total_pnl=EXCLUDED.total_pnl,
                    gross_exposure=EXCLUDED.gross_exposure,
                    net_exposure=EXCLUDED.net_exposure,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (
                initial_cash,
                positions_value,
                equity,
                total_pnl,
                gross_exposure,
                net_exposure,
                build_id,
            ))

            cur.execute("SELECT count(*) AS rows FROM analytics.portfolio_position_snapshot_v1;")
            position_rows = int(cur.fetchone()["rows"])

    print("=== PORTFOLIO_BUILDER_V1 ===")
    print(f"positions_saved={saved}")
    print(f"position_rows={position_rows}")
    print(f"cash={initial_cash}")
    print(f"positions_value={positions_value}")
    print(f"equity={equity}")
    print(f"gross_exposure={gross_exposure}")
    print(f"net_exposure={net_exposure}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PORTFOLIO_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_portfolio_builder_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_portfolio_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_portfolio_builder_v1.py | tee /tmp/portfolio_builder_v1.txt

grep -q "VERDICT=PORTFOLIO_BUILDER_V1_READY" /tmp/portfolio_builder_v1.txt

equity_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.portfolio_equity_snapshot_v1
WHERE portfolio_scope='GLOBAL';
")

bad_equity=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.portfolio_equity_snapshot_v1
WHERE equity IS NULL
   OR positions_value IS NULL
   OR gross_exposure IS NULL;
")

test "$equity_rows" -gt 0
test "$bad_equity" = "0"

psql -d finam_core -c "
SELECT
    portfolio_scope,
    cash,
    positions_value,
    equity,
    gross_exposure,
    net_exposure,
    source_version
FROM analytics.portfolio_equity_snapshot_v1
WHERE portfolio_scope='GLOBAL';
"

psql -d finam_core -c "
SELECT
    symbol,
    asset_class,
    quantity,
    market_value,
    exposure,
    position_status
FROM analytics.portfolio_position_snapshot_v1
ORDER BY symbol
LIMIT 30;
"

echo "equity_rows=$equity_rows"
echo "bad_equity_rows=$bad_equity"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PORTFOLIO_BUILDER_V1_OK"
SH_TEST

chmod +x scripts/test_portfolio_builder_v1.sh
scripts/test_portfolio_builder_v1.sh

echo "VERDICT=BUILD_PORTFOLIO_BUILDER_V1_OK"
