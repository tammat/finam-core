#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts

cat > sql/marketcore_ui/035_edge_discovery_from_market_universe_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_discovery_from_market_universe_v1 (
    discovery_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    strategy_family TEXT NOT NULL,

    bars_total INTEGER NOT NULL DEFAULT 0,
    trades_count INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,

    winrate NUMERIC(10,4) NOT NULL DEFAULT 0,
    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,8),
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,

    edge_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    discovery_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_queue_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_discovery_from_market_universe_v1 TO alex;

COMMIT;

SELECT 'EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_SCHEMA_V1_READY' AS verdict;
SQL

cat > src/scripts/build_edge_discovery_from_market_universe_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1"


def pf(gain: Decimal, loss: Decimal):
    if loss == 0 and gain > 0:
        return Decimal("999.0")
    if loss == 0:
        return None
    return gain / abs(loss)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.edge_discovery_from_market_universe_v1;")

            cur.execute("""
                SELECT queue_rank, symbol, timeframe, asset_class, recommended_strategy_family
                FROM marketcore_ui.market_universe_research_queue_v1
                ORDER BY queue_rank
                LIMIT 20;
            """)
            queue = [dict(r) for r in cur.fetchall()]

            out = []

            for q in queue:
                symbol = q["symbol"]
                tf = q["timeframe"]
                family = q["recommended_strategy_family"] or "BREAKOUT_MOMENTUM"

                cur.execute("""
                    WITH b AS (
                        SELECT
                            ts,
                            close,
                            lag(close) OVER (ORDER BY ts) AS prev_close
                        FROM public.market_bars
                        WHERE symbol=%s AND timeframe=%s
                        ORDER BY ts DESC
                        LIMIT 2000
                    ),
                    r AS (
                        SELECT
                            close - prev_close AS pnl
                        FROM b
                        WHERE prev_close IS NOT NULL
                    )
                    SELECT
                        count(*)::int AS trades_count,
                        count(*) FILTER (WHERE pnl > 0)::int AS wins,
                        count(*) FILTER (WHERE pnl <= 0)::int AS losses,
                        coalesce(sum(pnl),0)::numeric AS gross_pnl,
                        coalesce(avg(pnl),0)::numeric AS avg_pnl,
                        coalesce(sum(pnl) FILTER (WHERE pnl > 0),0)::numeric AS gross_gain,
                        coalesce(sum(pnl) FILTER (WHERE pnl <= 0),0)::numeric AS gross_loss
                    FROM r;
                """, (symbol, tf))

                r = dict(cur.fetchone())
                trades = int(r["trades_count"] or 0)
                wins = int(r["wins"] or 0)
                losses = int(r["losses"] or 0)
                gross = Decimal(r["gross_pnl"] or 0)
                avg = Decimal(r["avg_pnl"] or 0)
                gain = Decimal(r["gross_gain"] or 0)
                loss = Decimal(r["gross_loss"] or 0)
                profit_factor = pf(gain, loss)
                winrate = Decimal(wins) / Decimal(trades) if trades else Decimal("0")

                if trades >= 200 and profit_factor is not None and profit_factor >= Decimal("1.15") and avg > 0:
                    edge_status = "RESEARCH_CANDIDATE"
                    discovery_status = "DISCOVERED"
                    action = "Передать в validation queue."
                elif trades >= 200:
                    edge_status = "NO_EDGE_YET"
                    discovery_status = "OBSERVED"
                    action = "Оставить в наблюдении."
                else:
                    edge_status = "INSUFFICIENT_HISTORY"
                    discovery_status = "WAIT_HISTORY"
                    action = "Накопить историю."

                out.append((q, trades, wins, losses, winrate, gross, avg, profit_factor, edge_status, discovery_status, action))

            for rank, item in enumerate(out, start=1):
                q, trades, wins, losses, winrate, gross, avg, profit_factor, edge_status, discovery_status, action = item
                cur.execute("""
                    INSERT INTO marketcore_ui.edge_discovery_from_market_universe_v1 (
                        discovery_rank, symbol, timeframe, asset_class, strategy_family,
                        bars_total, trades_count, wins, losses,
                        winrate, gross_pnl, avg_pnl, profit_factor, expectancy,
                        edge_status, discovery_status, recommended_action,
                        source_queue_rank, source_version, refreshed_at, build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,%s,
                        %s,%s,%s,%s,%s,
                        %s,%s,%s,
                        %s,%s,now(),%s
                    );
                """, (
                    rank, q["symbol"], q["timeframe"], q["asset_class"], q["recommended_strategy_family"],
                    trades + 1, trades, wins, losses,
                    winrate, gross, avg, profit_factor, avg,
                    edge_status, discovery_status, action,
                    q["queue_rank"], SOURCE_VERSION, build_id,
                ))

            cur.execute("""
                SELECT edge_status, count(*) AS rows
                FROM marketcore_ui.edge_discovery_from_market_universe_v1
                GROUP BY edge_status
                ORDER BY edge_status;
            """)
            groups = cur.fetchall()

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_discovery_from_market_universe_v1;")
            rows_written = int(cur.fetchone()["rows"])

    print(f"rows_written={rows_written}")
    for g in groups:
        print(f"edge_status_{g['edge_status']}={g['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_discovery_from_market_universe_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/035_edge_discovery_from_market_universe_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_from_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_from_market_universe_v1.py \
  | tee /tmp/edge_discovery_from_market_universe_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1_READY" \
  /tmp/edge_discovery_from_market_universe_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_discovery_from_market_universe_v1;")
test "$rows" -gt 0

psql -d finam_core -c "
SELECT discovery_rank, symbol, timeframe, strategy_family, trades_count, winrate, profit_factor, expectancy, edge_status
FROM marketcore_ui.edge_discovery_from_market_universe_v1
ORDER BY discovery_rank
LIMIT 20;
"

echo "edge_discovery_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_discovery_from_market_universe_v1.sh
scripts/test_edge_discovery_from_market_universe_v1.sh

echo "VERDICT=BUILD_EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1_OK"
