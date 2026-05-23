from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE runtime_active_universe u
                SET
                    is_enabled = false,
                    disabled_at = now(),
                    disable_reason = 'runtime_governance_block: ' || g.decision || ' | ' || g.reason,
                    updated_at = now()
                FROM runtime_governance_decisions g
                WHERE u.symbol = g.symbol
                  AND COALESCE(u.strategy, '') = COALESCE(g.strategy, '')
                  AND COALESCE(u.timeframe, '') = COALESCE(g.timeframe, '')
                  AND g.allow_runtime = false
            """)

            blocked = cur.rowcount or 0

            cur.execute("""
                UPDATE runtime_active_universe u
                SET
                    disable_reason = 'runtime_governance_allow: ' || g.decision || ' | risk_multiplier=' || g.risk_multiplier::text,
                    updated_at = now()
                FROM runtime_governance_decisions g
                WHERE u.symbol = g.symbol
                  AND COALESCE(u.strategy, '') = COALESCE(g.strategy, '')
                  AND COALESCE(u.timeframe, '') = COALESCE(g.timeframe, '')
                  AND g.allow_runtime = true
                  AND u.is_enabled = true
            """)

            allowed = cur.rowcount or 0

        conn.commit()

    print(
        f"SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_GOVERNANCE_OK blocked={blocked} allowed={allowed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
