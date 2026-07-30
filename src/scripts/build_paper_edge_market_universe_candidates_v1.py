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

            # Timer and DB scheduler can overlap.  Serialize the replace cycle
            # inside PostgreSQL so DELETE + ranked INSERT is atomic to readers.
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (SOURCE_VERSION,))

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
