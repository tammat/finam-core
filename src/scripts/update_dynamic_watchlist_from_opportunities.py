from __future__ import annotations

import json
import os

from finam_core.data.postgres_opportunity_scanner import PostgresOpportunityScanner
from finam_core.storage.postgres_logger import PostgresLogger


LIMIT = int(os.getenv("OPPORTUNITY_WATCHLIST_LIMIT", "5"))


def main() -> int:
    pg = PostgresLogger()
    scanner = PostgresOpportunityScanner(pg)

    items = scanner.top_opportunities(limit=LIMIT)

    if not items:
        print("OK: no opportunities found")
        return 0

    with pg._connect() as conn:
        with conn.cursor() as cur:
            for x in items:
                raw = {
                    "atr_pct": x.atr_pct,
                    "rvol": x.rvol,
                    "turnover": x.turnover,
                    "spread_pct": x.spread_pct,
                    "regime": x.regime,
                    "opportunity_score": x.opportunity_score,
                    "strategy": x.strategy,
                    "source": "opportunity_scanner",
                }

                cur.execute(
                    """
                    insert into dynamic_watchlist (
                        symbol,
                        name,
                        direction,
                        score,
                        relative_strength,
                        portfolio_status,
                        portfolio_action,
                        source,
                        appearances,
                        score_delta,
                        persistence_state,
                        strategy,
                        regime,
                        priority,
                        is_active,
                        reason,
                        raw_json,
                        updated_at
                    )
                    values (
                        %s, %s, %s, %s, %s,
                        'WATCH',
                        %s,
                        'opportunity_scanner',
                        1,
                        0,
                        'ACTIVE',
                        %s, %s, %s, true, %s, %s::jsonb, now()
                    )
                    on conflict (symbol) do update set
                        ts = now(),
                        direction = excluded.direction,
                        score = excluded.score,
                        relative_strength = excluded.relative_strength,
                        portfolio_status = excluded.portfolio_status,
                        portfolio_action = excluded.portfolio_action,
                        source = excluded.source,
                        appearances = coalesce(dynamic_watchlist.appearances, 0) + 1,
                        score_delta = excluded.score - coalesce(dynamic_watchlist.score, 0),
                        persistence_state = excluded.persistence_state,
                        strategy = excluded.strategy,
                        regime = excluded.regime,
                        priority = excluded.priority,
                        is_active = excluded.is_active,
                        reason = excluded.reason,
                        raw_json = excluded.raw_json,
                        updated_at = now()
                    """,
                    (
                        x.symbol,
                        x.symbol,
                        "LONG" if "up" in x.regime or "trend" in x.regime else "WATCH",
                        x.opportunity_score,
                        x.rvol,
                        f"{x.strategy};regime={x.regime}",
                        x.strategy,
                        x.regime,
                        int(max(1, round(x.opportunity_score * 100))),
                        f"opportunity_score={x.opportunity_score};regime={x.regime}",
                        json.dumps(raw, ensure_ascii=False),
                    ),
                )

        conn.commit()

    for x in items:
        print(
            f"OPPORTUNITY_WATCHLIST symbol={x.symbol} "
            f"strategy={x.strategy} score={x.opportunity_score} regime={x.regime}"
        )

    print(f"OK: dynamic watchlist updated opportunities={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
