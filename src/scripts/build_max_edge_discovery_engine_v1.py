from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MAX_EDGE_DISCOVERY_ENGINE_V1"
OUT_JSON = Path("reports/max_edge_discovery_latest.json")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(type(obj).__name__)


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def score(row: dict) -> Decimal:
    net = d(row.get("net_after_tax"))
    dd = abs(d(row.get("max_drawdown")))
    trades = d(row.get("trades"))
    pf = d(row.get("profit_factor"))
    exp = d(row.get("expectancy"))

    raw = Decimal("50")
    raw += min(max(net, Decimal("-100")), Decimal("100")) * Decimal("0.20")
    raw += min(trades, Decimal("100")) * Decimal("0.20")
    raw += min(max(pf - Decimal("1"), Decimal("0")), Decimal("3")) * Decimal("10")
    raw += min(max(exp, Decimal("0")), Decimal("10")) * Decimal("2")
    raw -= min(dd, Decimal("100")) * Decimal("0.15")

    return max(Decimal("0"), min(Decimal("100"), raw)).quantize(Decimal("0.000001"))


def confidence(row: dict) -> Decimal:
    trades = d(row.get("trades"))
    return min(Decimal("100"), trades * Decimal("2")).quantize(Decimal("0.000001"))


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    rows_out = []

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT count(*) AS unsafe_rows
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true;
            """)
            unsafe_rows = int(cur.fetchone()["unsafe_rows"])

            cur.execute("""
                SELECT to_regclass('analytics.paper_portfolio_mtm_snapshot_v1') IS NOT NULL AS exists;
            """)
            paper_exists = bool(cur.fetchone()["exists"])

            source_table = "analytics.paper_portfolio_mtm_snapshot_v1" if paper_exists else "NONE"

            if paper_exists:
                cur.execute("""
                    SELECT
                        candidate_id::text AS candidate_id,
                        symbol::text AS symbol,
                        strategy_code::text AS strategy_code,
                        timeframe::text AS timeframe,
                        coalesce(trades,0)::int AS trades,
                        coalesce(net_after_tax,0)::numeric AS net_after_tax,
                        coalesce(max_drawdown,0)::numeric AS max_drawdown,
                        0::numeric AS expectancy,
                        0::numeric AS profit_factor
                    FROM analytics.paper_portfolio_mtm_snapshot_v1
                    ORDER BY snapshot_id DESC
                    LIMIT 200;
                """)
                source_rows = [dict(r) for r in cur.fetchall()]
            else:
                source_rows = []

            ranked = []
            for row in source_rows:
                row["edge_score"] = score(row)
                row["confidence"] = confidence(row)
                row["recommendation_code"] = "VALIDATE" if row["edge_score"] >= Decimal("70") else "RESEARCH"
                ranked.append(row)

            ranked = sorted(ranked, key=lambda r: (r["edge_score"], r["confidence"]), reverse=True)[:50]

            if not ranked:
                ranked = [{
                    "candidate_id": "NO_EDGE",
                    "symbol": "NO_DATA",
                    "strategy_code": "NO_DATA",
                    "timeframe": "NO_DATA",
                    "trades": 0,
                    "net_after_tax": Decimal("0"),
                    "max_drawdown": Decimal("0"),
                    "expectancy": Decimal("0"),
                    "profit_factor": Decimal("0"),
                    "edge_score": Decimal("0"),
                    "confidence": Decimal("0"),
                    "recommendation_code": "COLLECT_MORE_DATA",
                }]

            cur.execute("""
                DELETE FROM analytics.max_edge_ranking_v1
                WHERE source_version=%s;
            """, (SOURCE_VERSION,))

            for idx, row in enumerate(ranked, start=1):
                cur.execute("""
                    INSERT INTO analytics.max_edge_ranking_v1 (
                        rank_no,
                        candidate_id,
                        symbol,
                        strategy_code,
                        timeframe,
                        edge_score,
                        confidence,
                        expectancy,
                        profit_factor,
                        net_after_tax,
                        max_drawdown,
                        trades,
                        recommendation_code,
                        source_table,
                        status,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                """, (
                    idx,
                    row.get("candidate_id", ""),
                    row.get("symbol", ""),
                    row.get("strategy_code", ""),
                    row.get("timeframe", ""),
                    row.get("edge_score", 0),
                    row.get("confidence", 0),
                    row.get("expectancy", 0),
                    row.get("profit_factor", 0),
                    row.get("net_after_tax", 0),
                    row.get("max_drawdown", 0),
                    int(row.get("trades") or 0),
                    row.get("recommendation_code", "NO_ACTION"),
                    source_table,
                    "ACTIVE" if unsafe_rows == 0 else "BLOCKED",
                    SOURCE_VERSION,
                ))

            rows_out = ranked

    payload = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC),
        "rows": rows_out,
        "unsafe_rows": unsafe_rows,
        "verdict": "MAX_EDGE_DISCOVERY_ENGINE_READY" if unsafe_rows == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    print("=== MAX_EDGE_DISCOVERY_ENGINE_V1 ===")
    print(f"rows={len(rows_out)}")
    print(f"top_symbol={rows_out[0].get('symbol')}")
    print(f"top_score={rows_out[0].get('edge_score')}")
    print(f"unsafe_rows={unsafe_rows}")
    print(f"VERDICT={payload['verdict']}")


if __name__ == "__main__":
    main()
