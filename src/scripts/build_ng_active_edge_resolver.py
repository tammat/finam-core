from __future__ import annotations

from datetime import datetime, timezone

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.futures_session_classifier import classify_futures_session


def main() -> int:
    now = datetime.now(timezone.utc)
    current_session = classify_futures_session(now)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ng_active_edge_state (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    current_session TEXT NOT NULL,
                    required_regime_v2 TEXT NOT NULL,
                    governance_decision TEXT NOT NULL,
                    governance_allow_runtime BOOLEAN NOT NULL,
                    policy_matched BOOLEAN NOT NULL,
                    active_edge BOOLEAN NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe)
                );
            """)

            cur.execute("""
                SELECT symbol, strategy, timeframe,
                       governance_decision, allow_runtime, reason
                FROM ng_runtime_telemetry
                WHERE strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  AND timeframe='M1'
            """)

            rows = cur.fetchall()
            saved = 0

            for symbol, strategy, timeframe, gov_decision, gov_allow, gov_reason in rows:
                cur.execute("""
                    SELECT regime_v2, reason
                    FROM ng_m1_runtime_policy
                    WHERE symbol=%s
                      AND strategy=%s
                      AND timeframe=%s
                      AND session_bucket=%s
                      AND allow_runtime=true
                    ORDER BY profit_factor DESC, expectancy DESC, trades DESC
                    LIMIT 1
                """, (symbol, strategy, timeframe, current_session))

                policy = cur.fetchone()

                if policy:
                    required_regime_v2 = str(policy[0])
                    policy_reason = str(policy[1])
                    policy_matched = True
                else:
                    required_regime_v2 = "NO_ALLOWED_POLICY_FOR_SESSION"
                    policy_reason = f"нет_разрешенной_policy_для_session={current_session}"
                    policy_matched = False

                active_edge = bool(gov_allow) and policy_matched

                if active_edge:
                    reason = (
                        f"active_edge=true session={current_session} "
                        f"required_regime_v2={required_regime_v2}; {policy_reason}"
                    )
                else:
                    reason = (
                        f"active_edge=false session={current_session} "
                        f"governance_allow={gov_allow} policy_matched={policy_matched}; "
                        f"governance_reason={gov_reason}; policy_reason={policy_reason}"
                    )

                cur.execute("""
                    INSERT INTO ng_active_edge_state (
                        symbol, strategy, timeframe,
                        current_session, required_regime_v2,
                        governance_decision, governance_allow_runtime,
                        policy_matched, active_edge,
                        reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT(symbol, strategy, timeframe)
                    DO UPDATE SET
                        current_session=EXCLUDED.current_session,
                        required_regime_v2=EXCLUDED.required_regime_v2,
                        governance_decision=EXCLUDED.governance_decision,
                        governance_allow_runtime=EXCLUDED.governance_allow_runtime,
                        policy_matched=EXCLUDED.policy_matched,
                        active_edge=EXCLUDED.active_edge,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe,
                    current_session, required_regime_v2,
                    str(gov_decision), bool(gov_allow),
                    policy_matched, active_edge,
                    reason,
                ))

                print(
                    "NG_ACTIVE_EDGE_STATE "
                    f"symbol={symbol} session={current_session} "
                    f"required_regime_v2={required_regime_v2} "
                    f"governance={gov_decision} allow={gov_allow} "
                    f"policy_matched={policy_matched} active_edge={active_edge} "
                    f"reason={reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"NG_ACTIVE_EDGE_STATE_SUMMARY saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
