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
                    disable_reason = 'active_edge_block: ' || e.reason,
                    updated_at = now()
                FROM ng_active_edge_state e
                WHERE u.symbol = e.symbol
                  AND u.strategy = e.strategy
                  AND u.timeframe = e.timeframe
                  AND e.active_edge = false
            """)
            blocked = cur.rowcount or 0

            cur.execute("""
                UPDATE runtime_active_universe u
                SET
                    is_enabled = true,
                    disabled_at = NULL,
                    disable_reason = 'active_edge_allow: ' || e.reason,
                    updated_at = now()
                FROM ng_active_edge_state e
                WHERE u.symbol = e.symbol
                  AND u.strategy = e.strategy
                  AND u.timeframe = e.timeframe
                  AND e.active_edge = true
                  AND e.governance_allow_runtime = true
            """)
            allowed = cur.rowcount or 0

        conn.commit()

    print(
        f"SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_ACTIVE_EDGE_OK blocked={blocked} allowed={allowed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
