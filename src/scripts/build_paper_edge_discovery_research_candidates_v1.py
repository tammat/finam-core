from __future__ import annotations

import os
import uuid
from decimal import Decimal, InvalidOperation

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1"

SOURCE_TABLES = [
    "public.analytics_global_edge_expanded_runtime_candidates_v2",
    "public.analytics_global_edge_runtime_candidates_v2",
    "public.analytics_global_edge_top3_runtime_approval_board_v1",
]


def table_exists(cur, full_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s);", (full_name,))
    row = cur.fetchone()
    if row is None:
        return False
    if isinstance(row, dict):
        return next(iter(row.values())) is not None
    return row[0] is not None


def pick(row: dict, keys: list[str], default=None):
    for key in keys:
        if key in row and row[key] is not None:
            value = row[key]
            if isinstance(value, str) and value.strip() == "":
                continue
            return value
    return default


def as_text(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def as_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def as_int(value):
    if value is None:
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def candidate_score(candidate: dict) -> tuple:
    score = candidate.get("score")
    pf = candidate.get("profit_factor")
    expectancy = candidate.get("expectancy")
    net_pnl = candidate.get("net_pnl")
    trades = candidate.get("trades")

    def n(value):
        return float(value) if value is not None else -10**18

    return (
        n(score),
        n(pf),
        n(expectancy),
        n(net_pnl),
        n(trades),
    )


def load_candidates_from_table(cur, full_name: str) -> list[dict]:
    cur.execute(f"SELECT * FROM {full_name} LIMIT 2000;")
    rows = [dict(row) for row in cur.fetchall()]

    candidates: list[dict] = []

    for row in rows:
        symbol = as_text(pick(row, ["symbol", "ticker", "instrument", "secid"], ""))
        strategy = as_text(pick(row, ["strategy", "strategy_name", "model", "edge_name"], ""))
        timeframe = as_text(pick(row, ["timeframe", "tf", "horizon"], ""))
        side = as_text(pick(row, ["side", "direction"], ""))

        status = as_text(
            pick(
                row,
                ["candidate_status", "status", "board_decision", "decision", "verdict"],
                "CANDIDATE",
            ),
            "CANDIDATE",
        )

        expectancy = as_decimal(
            pick(row, ["expectancy", "expectancy_points", "avg_pnl", "mean_pnl"])
        )
        profit_factor = as_decimal(
            pick(row, ["profit_factor", "pf"])
        )
        winrate = as_decimal(
            pick(row, ["winrate", "win_rate", "win_rate_pct"])
        )
        trades = as_int(
            pick(row, ["closed_cycles", "closed_trades", "trades", "sample_size", "n_trades"])
        )
        net_pnl = as_decimal(
            pick(row, ["net_pnl", "pnl", "total_pnl", "gross_pnl"])
        )
        score = as_decimal(
            pick(row, ["edge_score", "score", "candidate_score", "top_score", "quality_score"])
        )

        if not symbol and not strategy:
            continue

        candidates.append(
            {
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": timeframe,
                "side": side,
                "candidate_status": status,
                "expectancy": expectancy,
                "profit_factor": profit_factor,
                "winrate": winrate,
                "trades": trades,
                "net_pnl": net_pnl,
                "score": score,
                "source_table": full_name,
            }
        )

    candidates.sort(key=candidate_score, reverse=True)
    return candidates[:20]


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1 ===")

            selected_source = "NONE"
            candidates: list[dict] = []

            for source_table in SOURCE_TABLES:
                if not table_exists(cur, source_table):
                    print(f"source_table={source_table} exists=0 rows=0")
                    continue

                table_candidates = load_candidates_from_table(cur, source_table)
                print(f"source_table={source_table} exists=1 candidates={len(table_candidates)}")

                if table_candidates:
                    selected_source = source_table
                    candidates = table_candidates
                    break

            cur.execute("DELETE FROM marketcore_ui.paper_edge_research_candidates_v1;")

            for idx, candidate in enumerate(candidates, start=1):
                cur.execute(
                    """
                    INSERT INTO marketcore_ui.paper_edge_research_candidates_v1 (
                        candidate_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        source_table,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                    """,
                    (
                        idx,
                        candidate["symbol"],
                        candidate["strategy"],
                        candidate["timeframe"],
                        candidate["side"],
                        candidate["candidate_status"],
                        candidate["expectancy"],
                        candidate["profit_factor"],
                        candidate["winrate"],
                        candidate["trades"],
                        candidate["net_pnl"],
                        candidate["score"],
                        candidate["source_table"],
                        SOURCE_VERSION,
                        build_id,
                    ),
                )

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_research_candidates_v1;")
            rows_written = int(cur.fetchone()["rows"])

    print(f"selected_source={selected_source}")
    print(f"rows_written={rows_written}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY")


if __name__ == "__main__":
    main()
