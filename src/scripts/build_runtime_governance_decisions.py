from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.runtime_governance_engine import (
    RuntimeGovernanceEngine,
    RuntimeGovernanceInput,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol-like", default="%")
    args = parser.parse_args()

    engine = RuntimeGovernanceEngine()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runtime_governance_decisions (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    allow_runtime BOOLEAN NOT NULL,
                    risk_multiplier NUMERIC NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe)
                );
            """)

            cur.execute("""
                SELECT
                    rs.symbol,
                    rs.strategy,
                    rs.timeframe,
                    rs.mode,
                    rs.enabled,
                    rs.reason,

                    COALESCE(er.event_status, 'NORMAL') AS event_status,
                    COALESCE(er.allow_runtime, true) AS event_allow_runtime,
                    COALESCE(er.risk_multiplier, 1.0) AS event_risk_multiplier,
                    COALESCE(er.reason, 'нет_значимых_событий') AS event_reason,

                    COALESCE(sp.session_bucket, 'UNKNOWN') AS session_bucket,
                    COALESCE(sp.allow_runtime, true) AS session_allow_runtime,
                    COALESCE(sp.reason, 'session_policy_missing_default_allow') AS session_reason,

                    CASE
                        WHEN rs.symbol LIKE 'NG%%'
                         AND rs.strategy = 'NG_CONSERVATIVE_BREAKOUT_M1'
                         AND rs.timeframe = 'M1'
                        THEN true
                        ELSE false
                    END AS ng_m1_policy_required,

                    COALESCE(ngp.allow_runtime, false) AS ng_m1_policy_allow_runtime,
                    COALESCE(ngp.reason, 'ng_m1_policy_missing_or_not_allowed') AS ng_m1_policy_reason

                FROM runtime_strategy_selection rs

                LEFT JOIN strategy_event_risk_context er
                    ON er.symbol = rs.symbol
                   AND er.strategy = rs.strategy
                   AND er.timeframe = rs.timeframe

                LEFT JOIN LATERAL (
                    SELECT p.*
                    FROM session_runtime_policy p
                    WHERE p.symbol = rs.symbol
                      AND p.strategy = rs.strategy
                      AND p.timeframe = rs.timeframe
                    ORDER BY p.allow_runtime DESC, p.calculated_at DESC
                    LIMIT 1
                ) sp ON TRUE

                LEFT JOIN LATERAL (
                    SELECT p.*
                    FROM ng_m1_runtime_policy p
                    WHERE p.symbol = rs.symbol
                      AND p.strategy = rs.strategy
                      AND p.timeframe = rs.timeframe
                      AND p.allow_runtime = true
                    ORDER BY p.profit_factor DESC, p.expectancy DESC, p.trades DESC
                    LIMIT 1
                ) ngp ON TRUE

                WHERE rs.symbol LIKE %s
                ORDER BY rs.symbol, rs.strategy, rs.timeframe
            """, (args.symbol_like,))

            rows = cur.fetchall()
            saved = 0

            for row in rows:
                decision = engine.decide(
                    RuntimeGovernanceInput(
                        symbol=str(row[0]),
                        strategy=str(row[1]),
                        timeframe=str(row[2]),
                        runtime_mode=str(row[3]),
                        runtime_enabled=bool(row[4]),
                        runtime_reason=str(row[5]),
                        event_status=str(row[6]),
                        event_allow_runtime=bool(row[7]),
                        event_risk_multiplier=float(row[8]),
                        event_reason=str(row[9]),
                        session_bucket=str(row[10]),
                        session_allow_runtime=bool(row[11]),
                        session_reason=str(row[12]),
                        ng_m1_policy_required=bool(row[13]),
                        ng_m1_policy_allow_runtime=bool(row[14]),
                        ng_m1_policy_reason=str(row[15]),
                    )
                )

                cur.execute("""
                    INSERT INTO runtime_governance_decisions (
                        symbol, strategy, timeframe,
                        decision, allow_runtime, risk_multiplier,
                        reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe)
                    DO UPDATE SET
                        decision=EXCLUDED.decision,
                        allow_runtime=EXCLUDED.allow_runtime,
                        risk_multiplier=EXCLUDED.risk_multiplier,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    decision.symbol,
                    decision.strategy,
                    decision.timeframe,
                    decision.decision,
                    decision.allow_runtime,
                    decision.risk_multiplier,
                    decision.reason,
                ))

                print(
                    "RUNTIME_GOVERNANCE_DECISION "
                    f"symbol={decision.symbol} strategy={decision.strategy} "
                    f"timeframe={decision.timeframe} decision={decision.decision} "
                    f"allow={decision.allow_runtime} multiplier={decision.risk_multiplier} "
                    f"reason={decision.reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"RUNTIME_GOVERNANCE_DECISIONS_SUMMARY saved={saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
