from __future__ import annotations

import os
import re
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1"

MONTH_CODES = set("FGHJKMNQUVXZ")


def clean_symbol(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def candidate_root(symbol: str) -> str:
    raw = (symbol or "").upper()
    base = raw.split("@", 1)[0]
    base = base.replace("_ROLLING", "").replace("_CONT", "").replace("CONT", "")

    # BRN6 -> BR, NGM6 -> NG, GDU6 -> GD
    if len(base) >= 4 and base[-2:].isalnum() and base[-2:-1] in MONTH_CODES and base[-1:].isdigit():
        return base[:-2]

    # USDRUBF -> USDRUB, SiH6 -> SI etc.
    if len(base) >= 4 and base[-1:] in MONTH_CODES:
        return base[:-1]

    return re.sub(r"[^A-Z0-9]", "", base)


def score_alias(candidate_symbol: str, market_symbol: str) -> tuple[str, Decimal]:
    c_clean = clean_symbol(candidate_symbol)
    m_clean = clean_symbol(market_symbol)
    root = candidate_root(candidate_symbol)

    if not c_clean or not m_clean:
        return "NO_MATCH", Decimal("0.0000")

    if c_clean == m_clean:
        return "EXACT_CLEAN_MATCH", Decimal("1.0000")

    if candidate_symbol.upper() == market_symbol.upper():
        return "EXACT_SYMBOL_MATCH", Decimal("1.0000")

    if root and m_clean == root:
        return "ROOT_EXACT_MATCH", Decimal("0.9500")

    if root and (m_clean.startswith(root) or root.startswith(m_clean)):
        return "ROOT_PREFIX_MATCH", Decimal("0.8500")

    if root and root in m_clean:
        return "ROOT_CONTAINS_MATCH", Decimal("0.7500")

    c_prefix = c_clean[:3]
    m_prefix = m_clean[:3]
    if c_prefix and c_prefix == m_prefix:
        return "PREFIX3_MATCH", Decimal("0.6500")

    c_prefix2 = c_clean[:2]
    m_prefix2 = m_clean[:2]
    if c_prefix2 and c_prefix2 == m_prefix2:
        return "PREFIX2_MATCH", Decimal("0.5000")

    return "NO_MATCH", Decimal("0.0000")


def classify(match_type: str, confidence: Decimal, age_sec) -> tuple[str, str, str]:
    if match_type == "NO_MATCH":
        return (
            "NO_ALIAS_FOUND",
            "Не найден подходящий market symbol.",
            "Добавить ручной alias или проверить backfill market_bars.",
        )

    if age_sec is None:
        return (
            "ALIAS_FOUND_UNKNOWN_FRESHNESS",
            "Похожий market symbol найден, но свежесть не определена.",
            "Проверить timestamp market_bars.",
        )

    if confidence >= Decimal("0.85"):
        return (
            "ALIAS_CANDIDATE_STRONG",
            "Найден сильный кандидат на alias для market data binding.",
            "Добавить alias в следующий слой alias-словаря и повторить binding.",
        )

    if confidence >= Decimal("0.50"):
        return (
            "ALIAS_CANDIDATE_WEAK",
            "Найден слабый кандидат на alias, требуется ручная проверка.",
            "Проверить соответствие инструмента вручную до применения.",
        )

    return (
        "NO_ALIAS_FOUND",
        "Совпадение недостаточно сильное.",
        "Не применять автоматически.",
    )


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1 ===")

            cur.execute("""
                SELECT
                    freshness_rank,
                    candidate_symbol,
                    candidate_strategy,
                    candidate_timeframe,
                    side
                FROM marketcore_ui.paper_edge_market_data_freshness_v1
                WHERE row_type='CANDIDATE_BINDING'
                ORDER BY freshness_rank;
            """)
            candidates = [dict(row) for row in cur.fetchall()]

            cur.execute("""
                SELECT
                    freshness_rank,
                    market_symbol,
                    market_timeframe,
                    source_table,
                    bars_total,
                    latest_bar_ts,
                    market_data_age_sec
                FROM marketcore_ui.paper_edge_market_data_freshness_v1
                WHERE row_type='SOURCE_LATEST'
                ORDER BY market_symbol, market_timeframe;
            """)
            market_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")

            plan_rows: list[dict] = []

            for candidate in candidates:
                symbol = str(candidate.get("candidate_symbol") or "")
                root = candidate_root(symbol)

                scored: list[dict] = []

                for market in market_rows:
                    market_symbol = str(market.get("market_symbol") or "")
                    match_type, confidence = score_alias(symbol, market_symbol)

                    if confidence <= Decimal("0"):
                        continue

                    alias_status, diagnosis, action = classify(
                        match_type=match_type,
                        confidence=confidence,
                        age_sec=market.get("market_data_age_sec"),
                    )

                    scored.append(
                        {
                            "candidate_symbol": symbol,
                            "candidate_root": root,
                            "candidate_strategy": candidate.get("candidate_strategy") or "",
                            "candidate_timeframe": candidate.get("candidate_timeframe") or "",
                            "side": candidate.get("side") or "",
                            "alias_symbol": market_symbol,
                            "alias_timeframe": market.get("market_timeframe") or "",
                            "alias_source_table": market.get("source_table") or "",
                            "alias_bars_total": int(market.get("bars_total") or 0),
                            "alias_latest_bar_ts": market.get("latest_bar_ts"),
                            "alias_market_data_age_sec": market.get("market_data_age_sec"),
                            "alias_match_type": match_type,
                            "alias_confidence": confidence,
                            "alias_status": alias_status,
                            "diagnosis": diagnosis,
                            "recommended_action": action,
                            "source_freshness_rank": market.get("freshness_rank"),
                        }
                    )

                scored.sort(
                    key=lambda row: (
                        row["alias_confidence"],
                        row["alias_bars_total"],
                        -(row["alias_market_data_age_sec"] or 999999999),
                    ),
                    reverse=True,
                )

                if scored:
                    plan_rows.extend(scored[:3])
                else:
                    plan_rows.append(
                        {
                            "candidate_symbol": symbol,
                            "candidate_root": root,
                            "candidate_strategy": candidate.get("candidate_strategy") or "",
                            "candidate_timeframe": candidate.get("candidate_timeframe") or "",
                            "side": candidate.get("side") or "",
                            "alias_symbol": "",
                            "alias_timeframe": "",
                            "alias_source_table": "",
                            "alias_bars_total": 0,
                            "alias_latest_bar_ts": None,
                            "alias_market_data_age_sec": None,
                            "alias_match_type": "NO_MATCH",
                            "alias_confidence": Decimal("0.0000"),
                            "alias_status": "NO_ALIAS_FOUND",
                            "diagnosis": "По кандидату не найден похожий market symbol среди свежих market bars.",
                            "recommended_action": "Добавить ручной alias или проверить backfill market_bars.",
                            "source_freshness_rank": candidate.get("freshness_rank"),
                        }
                    )

            for idx, row in enumerate(plan_rows, start=1):
                cur.execute("""
                    INSERT INTO marketcore_ui.paper_edge_market_symbol_alias_plan_v1 (
                        plan_rank,
                        candidate_symbol,
                        candidate_root,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        alias_symbol,
                        alias_timeframe,
                        alias_source_table,
                        alias_bars_total,
                        alias_latest_bar_ts,
                        alias_market_data_age_sec,
                        alias_match_type,
                        alias_confidence,
                        alias_status,
                        diagnosis,
                        recommended_action,
                        source_freshness_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row["candidate_symbol"],
                    row["candidate_root"],
                    row["candidate_strategy"],
                    row["candidate_timeframe"],
                    row["side"],
                    row["alias_symbol"],
                    row["alias_timeframe"],
                    row["alias_source_table"],
                    row["alias_bars_total"],
                    row["alias_latest_bar_ts"],
                    row["alias_market_data_age_sec"],
                    row["alias_match_type"],
                    row["alias_confidence"],
                    row["alias_status"],
                    row["diagnosis"],
                    row["recommended_action"],
                    row["source_freshness_rank"],
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT alias_status, count(*) AS rows
                FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
                GROUP BY alias_status
                ORDER BY alias_status;
            """)
            status_rows = cur.fetchall()

    print(f"candidates={len(candidates)}")
    print(f"market_rows={len(market_rows)}")
    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"alias_status_{row['alias_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY")


if __name__ == "__main__":
    main()
