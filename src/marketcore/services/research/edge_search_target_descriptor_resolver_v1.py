from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from psycopg2.extras import RealDictCursor


@dataclass(frozen=True)
class TargetDescriptorV1:
    symbol: str
    research_family: str
    strategy: str
    side: str
    authority_source: str
    authority_rows: int
    state: str
    reason: str


def _resolve_unique_leader(
    rows: list[dict],
    *,
    symbol: str,
    research_family: str,
    authority_source: str,
) -> TargetDescriptorV1:
    if not rows:
        return TargetDescriptorV1(
            symbol=symbol,
            research_family=research_family,
            strategy="",
            side="",
            authority_source=authority_source,
            authority_rows=0,
            state="UNRESOLVED",
            reason="NO_AUTHORITATIVE_DESCRIPTOR",
        )

    ranked = sorted(
        rows,
        key=lambda r: (
            int(r["rows"]),
            str(r["strategy_code"]),
            str(r["side_code"]),
        ),
        reverse=True,
    )

    top = ranked[0]

    if len(ranked) > 1 and int(ranked[1]["rows"]) == int(top["rows"]):
        return TargetDescriptorV1(
            symbol=symbol,
            research_family=research_family,
            strategy="",
            side="",
            authority_source=authority_source,
            authority_rows=int(top["rows"]),
            state="UNRESOLVED",
            reason="AMBIGUOUS_AUTHORITATIVE_DESCRIPTOR",
        )

    return TargetDescriptorV1(
        symbol=symbol,
        research_family=research_family,
        strategy=str(top["strategy_code"]),
        side=str(top["side_code"]).upper(),
        authority_source=authority_source,
        authority_rows=int(top["rows"]),
        state="RESOLVED",
        reason="UNIQUE_AUTHORITATIVE_LEADER",
    )


def resolve_target_descriptor_v1(
    conn,
    *,
    symbol: str,
    research_family: str,
) -> TargetDescriptorV1:
    family = research_family.strip().upper()
    physical_symbol = symbol.strip()

    if not physical_symbol or "@" not in physical_symbol:
        return TargetDescriptorV1(
            symbol=physical_symbol,
            research_family=family,
            strategy="",
            side="",
            authority_source="",
            authority_rows=0,
            state="UNRESOLVED",
            reason="PHYSICAL_SYMBOL_REQUIRED",
        )

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if family == "EXIT_OOS":
            cur.execute(
                """
                SELECT
                    strategy_code,
                    side_code,
                    count(*)::bigint AS rows
                FROM analytics.trade_outcome_hypothesis_active_v4
                WHERE symbol=%s
                GROUP BY strategy_code,side_code
                ORDER BY rows DESC,strategy_code,side_code
                """,
                (physical_symbol,),
            )
            return _resolve_unique_leader(
                list(cur.fetchall()),
                symbol=physical_symbol,
                research_family=family,
                authority_source=(
                    "analytics.trade_outcome_hypothesis_active_v4"
                ),
            )

        if family == "ECONOMIC_OOS":
            cur.execute(
                """
                SELECT
                    strategy_code,
                    side_code,
                    count(*)::bigint AS rows
                FROM analytics.hierarchical_evidence_v1
                WHERE symbol_code=%s
                GROUP BY strategy_code,side_code
                ORDER BY rows DESC,strategy_code,side_code
                """,
                (physical_symbol,),
            )
            return _resolve_unique_leader(
                list(cur.fetchall()),
                symbol=physical_symbol,
                research_family=family,
                authority_source="analytics.hierarchical_evidence_v1",
            )

    return TargetDescriptorV1(
        symbol=physical_symbol,
        research_family=family,
        strategy="",
        side="",
        authority_source="",
        authority_rows=0,
        state="UNRESOLVED",
        reason="UNSUPPORTED_RESEARCH_FAMILY",
    )
