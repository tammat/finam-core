from __future__ import annotations

import argparse
from datetime import datetime, timezone

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.futures_session_classifier import classify_futures_session


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol-like", default="%@RTSX")
    args = parser.parse_args()

    current_session = classify_futures_session(datetime.now(timezone.utc))

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, strategy, timeframe, mode, enabled, reason
                FROM runtime_strategy_selection
                WHERE symbol LIKE %s
            """, (args.symbol_like,))

            rows = cur.fetchall()
            updated = 0

            for symbol, strategy, timeframe, mode, enabled, reason in rows:
                cur.execute("""
                    SELECT allow_runtime, reason
                    FROM session_runtime_policy
                    WHERE symbol=%s
                      AND strategy=%s
                      AND timeframe=%s
                      AND session_bucket=%s
                    LIMIT 1
                """, (symbol, strategy, timeframe, current_session))

                policy = cur.fetchone()

                if not policy:
                    allow_runtime = False
                    policy_reason = f"нет_session_policy_для_{current_session}"
                else:
                    allow_runtime = bool(policy[0])
                    policy_reason = str(policy[1])

                if enabled and not allow_runtime:
                    cur.execute("""
                        UPDATE runtime_strategy_selection
                        SET mode='SESSION_BLOCKED',
                            enabled=false,
                            reason=%s,
                            updated_at=now()
                        WHERE symbol=%s
                          AND strategy=%s
                          AND timeframe=%s
                    """, (
                        f"session_gate_block: current_session={current_session}; {policy_reason}",
                        symbol, strategy, timeframe,
                    ))
                    updated += cur.rowcount or 0

                elif current_session != "CLOSED":
                    cur.execute("""
                        UPDATE runtime_strategy_selection
                        SET reason = reason || %s,
                            updated_at=now()
                        WHERE symbol=%s
                          AND strategy=%s
                          AND timeframe=%s
                          AND position(%s in reason) = 0
                    """, (
                        f" | current_session={current_session}",
                        symbol, strategy, timeframe,
                        f"current_session={current_session}",
                    ))

            conn.commit()

    print(
        "SESSION_RUNTIME_GATE_OK "
        f"current_session={current_session} checked={len(rows)} updated={updated}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
