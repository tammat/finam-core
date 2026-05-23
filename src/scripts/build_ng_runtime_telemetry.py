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
                CREATE TABLE IF NOT EXISTS ng_runtime_telemetry (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    current_session TEXT NOT NULL,
                    current_regime_v2 TEXT NOT NULL,
                    policy_matched BOOLEAN NOT NULL,
                    governance_decision TEXT NOT NULL,
                    allow_runtime BOOLEAN NOT NULL,
                    risk_multiplier NUMERIC NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe)
                );
            """)

            cur.execute("""
                SELECT symbol, strategy, timeframe, decision, allow_runtime, risk_multiplier, reason
                FROM runtime_governance_decisions
                WHERE symbol LIKE 'NG%%'
                  AND strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  AND timeframe='M1'
            """)

            rows = cur.fetchall()
            saved = 0

            for symbol, strategy, timeframe, decision, allow_runtime, risk_multiplier, reason in rows:
                cur.execute("""
                    SELECT regime_v2
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
                    current_regime_v2 = str(policy[0])
                    policy_matched = True
                else:
                    current_regime_v2 = "NO_ALLOWED_POLICY_FOR_SESSION"
                    policy_matched = False

                cur.execute("""
                    INSERT INTO ng_runtime_telemetry (
                        symbol, strategy, timeframe,
                        current_session, current_regime_v2,
                        policy_matched,
                        governance_decision, allow_runtime, risk_multiplier,
                        reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT(symbol, strategy, timeframe)
                    DO UPDATE SET
                        current_session=EXCLUDED.current_session,
                        current_regime_v2=EXCLUDED.current_regime_v2,
                        policy_matched=EXCLUDED.policy_matched,
                        governance_decision=EXCLUDED.governance_decision,
                        allow_runtime=EXCLUDED.allow_runtime,
                        risk_multiplier=EXCLUDED.risk_multiplier,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe,
                    current_session, current_regime_v2,
                    policy_matched,
                    decision, allow_runtime, risk_multiplier,
                    reason,
                ))

                print(
                    "NG_RUNTIME_TELEMETRY "
                    f"symbol={symbol} session={current_session} regime_v2={current_regime_v2} "
                    f"policy_matched={policy_matched} decision={decision} "
                    f"allow={allow_runtime} multiplier={risk_multiplier} reason={reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"NG_RUNTIME_TELEMETRY_SUMMARY saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
