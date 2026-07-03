#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts

cat > sql/marketcore_ui/032_paper_edge_market_universe_candidates_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_universe_candidates_v1 (
    candidate_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'UNKNOWN',

    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    data_age_sec INTEGER,

    universe_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    candidate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    score NUMERIC(10,4) NOT NULL DEFAULT 0,

    recommended_action TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual',

    UNIQUE(symbol, timeframe)
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_universe_candidates_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_UNIVERSE_CANDIDATES_SCHEMA_V1_READY' AS verdict;
SQL

cat > src/scripts/build_paper_edge_market_universe_candidates_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1"
MIN_BARS = int(os.getenv("MARKET_UNIVERSE_MIN_BARS", "200"))
MAX_AGE_SEC = int(os.getenv("MARKET_UNIVERSE_MAX_AGE_SEC", "172800"))


def asset_class(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith("@MISX"):
        return "EQUITY_OR_FX_SPOT"
    if s.endswith("@RTSX"):
        return "FUTURES"
    if s in {"BTCUSD", "ETHUSD"}:
        return "CRYPTO_PROXY"
    if s == "IMOEX":
        return "INDEX"
    return "UNKNOWN"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")

            cur.execute("""
                WITH latest AS (
                    SELECT DISTINCT ON (symbol, timeframe)
                        symbol,
                        timeframe,
                        ts AS latest_ts,
                        close AS latest_close,
                        volume AS latest_volume
                    FROM public.market_bars
                    ORDER BY symbol, timeframe, ts DESC
                ),
                agg AS (
                    SELECT
                        symbol,
                        timeframe,
                        count(*)::int AS bars_total,
                        max(ts) AS latest_ts,
                        extract(epoch FROM (now() - max(ts)))::int AS data_age_sec
                    FROM public.market_bars
                    GROUP BY symbol, timeframe
                )
                SELECT
                    a.symbol,
                    a.timeframe,
                    a.bars_total,
                    a.latest_ts,
                    l.latest_close,
                    l.latest_volume,
                    a.data_age_sec
                FROM agg a
                JOIN latest l
                  ON l.symbol=a.symbol
                 AND l.timeframe=a.timeframe
                WHERE a.bars_total >= %s
                ORDER BY
                    CASE a.timeframe
                        WHEN 'M5' THEN 1
                        WHEN 'M1' THEN 2
                        WHEN 'H1' THEN 3
                        ELSE 9
                    END,
                    a.latest_ts DESC,
                    a.bars_total DESC,
                    a.symbol
                LIMIT 200;
            """, (MIN_BARS,))

            rows = [dict(r) for r in cur.fetchall()]

            for rank, row in enumerate(rows, start=1):
                age = int(row["data_age_sec"] or 999999999)
                bars = int(row["bars_total"] or 0)

                fresh = age <= MAX_AGE_SEC
                ready = fresh and bars >= MIN_BARS

                status = "FRESH" if fresh else "STALE"
                candidate_status = "MARKET_CANDIDATE" if ready else "WAIT_FRESH_DATA"

                score = min(1.0, bars / 10000.0)
                if fresh:
                    score += 0.5
                if row["timeframe"] == "M5":
                    score += 0.25
                score = min(score, 1.0)

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_edge_market_universe_candidates_v1 (
                        candidate_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        bars_total,
                        latest_ts,
                        latest_close,
                        latest_volume,
                        data_age_sec,
                        universe_status,
                        candidate_status,
                        score,
                        recommended_action,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    rank,
                    row["symbol"],
                    row["timeframe"],
                    asset_class(row["symbol"]),
                    bars,
                    row["latest_ts"],
                    row["latest_close"],
                    row["latest_volume"],
                    age,
                    status,
                    candidate_status,
                    score,
                    "Использовать как market-universe candidate для дальнейшего edge discovery." if ready else "Ждать свежих данных.",
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT asset_class, timeframe, candidate_status, count(*) AS rows
                FROM marketcore_ui.paper_edge_market_universe_candidates_v1
                GROUP BY asset_class, timeframe, candidate_status
                ORDER BY asset_class, timeframe, candidate_status;
            """)
            groups = cur.fetchall()

    print(f"rows_written={rows_written}")
    print(f"min_bars={MIN_BARS}")
    print(f"max_age_sec={MAX_AGE_SEC}")
    for g in groups:
        print(
            f"GROUP asset_class={g['asset_class']} "
            f"timeframe={g['timeframe']} "
            f"status={g['candidate_status']} "
            f"rows={g['rows']}"
        )
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_paper_edge_discovery_market_universe_candidates_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/032_paper_edge_market_universe_candidates_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_universe_candidates_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py \
  | tee /tmp/paper_edge_market_universe_candidates_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_READY" \
  /tmp/paper_edge_market_universe_candidates_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")
br_only=$(psql -At -d finam_core -c "SELECT count(*) = count(*) FILTER (WHERE symbol LIKE 'BR%') FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$br_only" = "f"

psql -d finam_core -c "
SELECT candidate_rank, symbol, timeframe, asset_class, bars_total, latest_ts, universe_status, candidate_status, score
FROM marketcore_ui.paper_edge_market_universe_candidates_v1
ORDER BY candidate_rank
LIMIT 40;
"

echo "market_universe_rows=$rows"
echo "market_universe_symbols=$symbols"
echo "br_only=$br_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_market_universe_candidates_v1.sh

scripts/test_paper_edge_discovery_market_universe_candidates_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1_OK"
