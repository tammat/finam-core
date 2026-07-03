from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_UNIVERSE_RANKING_V1"


def clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def timeframe_score(tf: str) -> float:
    return {"M5": 1.0, "M1": 0.85, "H1": 0.70, "M15": 0.65}.get(tf, 0.4)


def asset_priority(asset: str) -> float:
    return {
        "FUTURES": 1.0,
        "EQUITY_OR_FX_SPOT": 0.95,
        "CRYPTO_PROXY": 0.75,
        "INDEX": 0.60,
    }.get(asset, 0.40)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MARKET_UNIVERSE_RANKING_V1 ===")

            cur.execute("""
                SELECT *
                FROM marketcore_ui.paper_edge_market_universe_candidates_v1
                ORDER BY candidate_rank;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.market_universe_ranking_v1;")

            ranked = []
            max_volume = max([float(r.get("latest_volume") or 0) for r in rows] or [1.0])

            for r in rows:
                age = int(r.get("data_age_sec") or 999999999)
                bars = int(r.get("bars_total") or 0)
                volume = float(r.get("latest_volume") or 0)
                tf = str(r.get("timeframe") or "")
                asset = str(r.get("asset_class") or "UNKNOWN")

                freshness = clamp(1.0 - age / 172800.0)
                history = clamp(bars / 10000.0)
                liquidity = clamp(volume / max_volume) if max_volume > 0 else 0.0
                tf_score = timeframe_score(tf)
                asset_score = asset_priority(asset)

                total = (
                    freshness * 35.0 +
                    history * 25.0 +
                    liquidity * 15.0 +
                    tf_score * 15.0 +
                    asset_score * 10.0
                )

                if total >= 80:
                    status = "READY_FOR_RESEARCH"
                    action = "Добавить в TOP research queue."
                elif freshness < 0.2:
                    status = "WAIT_FRESH_DATA"
                    action = "Ждать обновления market bars."
                else:
                    status = "WATCHLIST"
                    action = "Оставить в наблюдении."

                ranked.append((total, r, freshness, history, liquidity, tf_score, asset_score, status, action))

            ranked.sort(key=lambda x: x[0], reverse=True)

            for rank, item in enumerate(ranked, start=1):
                total, r, freshness, history, liquidity, tf_score, asset_score, status, action = item

                cur.execute("""
                    INSERT INTO marketcore_ui.market_universe_ranking_v1 (
                        rank, symbol, timeframe, asset_class,
                        bars_total, latest_ts, latest_close, latest_volume, data_age_sec,
                        freshness_score, history_score, liquidity_score, timeframe_score,
                        asset_priority_score, total_score,
                        ranking_status, recommended_action,
                        source_version, refreshed_at, build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    rank, r["symbol"], r["timeframe"], r["asset_class"],
                    r["bars_total"], r["latest_ts"], r["latest_close"], r["latest_volume"], r["data_age_sec"],
                    freshness * 100, history * 100, liquidity * 100, tf_score * 100,
                    asset_score * 100, total,
                    status, action,
                    SOURCE_VERSION, build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.market_universe_ranking_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT ranking_status, count(*) AS rows
                FROM marketcore_ui.market_universe_ranking_v1
                GROUP BY ranking_status
                ORDER BY ranking_status;
            """)
            groups = cur.fetchall()

    print(f"rows_written={rows_written}")
    for g in groups:
        print(f"ranking_status_{g['ranking_status']}={g['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_UNIVERSE_RANKING_V1_READY")


if __name__ == "__main__":
    main()
