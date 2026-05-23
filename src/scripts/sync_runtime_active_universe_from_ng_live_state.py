from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO runtime_active_universe (
                    symbol,
                    strategy,
                    timeframe,
                    regime,
                    score,
                    priority,
                    is_enabled,
                    allocated_at,
                    last_seen_at,
                    disabled_at,
                    disable_reason,
                    source,
                    raw_json,
                    updated_at
                )
                SELECT
                    s.symbol,
                    s.strategy,
                    s.timeframe,
                    s.runtime_state AS regime,
                    CASE WHEN s.runtime_state = 'ACTIVE' THEN 1.0 ELSE 0.0 END AS score,
                    100 AS priority,
                    CASE WHEN s.runtime_state = 'ACTIVE' THEN true ELSE false END AS is_enabled,
                    now() AS allocated_at,
                    now() AS last_seen_at,
                    CASE WHEN s.runtime_state = 'ACTIVE' THEN NULL ELSE now() END AS disabled_at,
                    CASE
                        WHEN s.runtime_state = 'ACTIVE'
                        THEN 'ng_live_state_allow: ACTIVE | ' || s.state_reason
                        ELSE 'ng_live_state_block: ' || s.runtime_state || ' | ' || s.state_reason
                    END AS disable_reason,
                    'ng_live_runtime_state' AS source,
                    jsonb_build_object(
                        'runtime_state', s.runtime_state,
                        'allow_new_entries', s.allow_new_entries,
                        'allow_position_management', s.allow_position_management,
                        'active_edge', s.active_edge,
                        'governance_allow', s.governance_allow,
                        'market_data_fresh', s.market_data_fresh,
                        'open_position_qty', s.open_position_qty,
                        'state_reason', s.state_reason
                    ) AS raw_json,
                    now() AS updated_at
                FROM ng_live_runtime_state s
                ON CONFLICT (symbol)
                DO UPDATE SET
                    strategy = EXCLUDED.strategy,
                    timeframe = EXCLUDED.timeframe,
                    regime = EXCLUDED.regime,
                    score = EXCLUDED.score,
                    priority = EXCLUDED.priority,
                    is_enabled = EXCLUDED.is_enabled,
                    last_seen_at = EXCLUDED.last_seen_at,
                    disabled_at = EXCLUDED.disabled_at,
                    disable_reason = EXCLUDED.disable_reason,
                    source = EXCLUDED.source,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = now()
            """)
            upserted = cur.rowcount or 0

        conn.commit()

    print(f"SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_NG_LIVE_STATE_OK upserted={upserted}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
