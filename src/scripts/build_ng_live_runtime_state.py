from __future__ import annotations

from datetime import datetime, timezone, timedelta

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.ng_live_runtime_state_machine import (
    NgLiveRuntimeInput,
    NgLiveRuntimeStateMachine,
)


def main() -> int:
    now = datetime.now(timezone.utc)
    freshness_cutoff = now - timedelta(minutes=10)
    machine = NgLiveRuntimeStateMachine()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ng_live_runtime_state (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    runtime_state TEXT NOT NULL,
                    allow_new_entries BOOLEAN NOT NULL,
                    allow_position_management BOOLEAN NOT NULL,
                    active_edge BOOLEAN NOT NULL,
                    governance_allow BOOLEAN NOT NULL,
                    market_data_fresh BOOLEAN NOT NULL,
                    open_position_qty NUMERIC NOT NULL DEFAULT 0,
                    state_reason TEXT NOT NULL,
                    entered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe)
                );
            """)

            cur.execute("""
                SELECT
                    e.symbol,
                    e.strategy,
                    e.timeframe,
                    e.active_edge,
                    e.governance_allow_runtime,
                    COALESCE(s.runtime_state, 'DISABLED') AS previous_state
                FROM ng_active_edge_state e
                LEFT JOIN ng_live_runtime_state s
                  ON s.symbol=e.symbol
                 AND s.strategy=e.strategy
                 AND s.timeframe=e.timeframe
            """)

            rows = cur.fetchall()
            saved = 0

            for symbol, strategy, timeframe, active_edge, governance_allow, previous_state in rows:
                cur.execute("""
                    SELECT max(ts)
                    FROM market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                """, (symbol, timeframe))
                last_bar_ts = cur.fetchone()[0]
                market_data_fresh = bool(last_bar_ts and last_bar_ts >= freshness_cutoff)

                cur.execute("""
                    SELECT COALESCE(
                        sum(
                            CASE
                                WHEN upper(side) = 'BUY' THEN COALESCE(filled_qty, qty, 0)
                                WHEN upper(side) = 'SELL' THEN -COALESCE(filled_qty, qty, 0)
                                ELSE 0
                            END
                        ),
                        0
                    )
                    FROM broker_order_snapshots
                    WHERE symbol=%s
                """, (symbol,))
                row = cur.fetchone()
                open_position_qty = float(row[0] or 0)

                decision = machine.decide(
                    NgLiveRuntimeInput(
                        symbol=str(symbol),
                        strategy=str(strategy),
                        timeframe=str(timeframe),
                        previous_state=str(previous_state),
                        active_edge=bool(active_edge),
                        governance_allow=bool(governance_allow),
                        market_data_fresh=market_data_fresh,
                        open_position_qty=open_position_qty,
                    )
                )

                cur.execute("""
                    INSERT INTO ng_live_runtime_state (
                        symbol, strategy, timeframe,
                        runtime_state,
                        allow_new_entries,
                        allow_position_management,
                        active_edge,
                        governance_allow,
                        market_data_fresh,
                        open_position_qty,
                        state_reason,
                        entered_at,
                        updated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now())
                    ON CONFLICT(symbol, strategy, timeframe)
                    DO UPDATE SET
                        runtime_state=EXCLUDED.runtime_state,
                        allow_new_entries=EXCLUDED.allow_new_entries,
                        allow_position_management=EXCLUDED.allow_position_management,
                        active_edge=EXCLUDED.active_edge,
                        governance_allow=EXCLUDED.governance_allow,
                        market_data_fresh=EXCLUDED.market_data_fresh,
                        open_position_qty=EXCLUDED.open_position_qty,
                        state_reason=EXCLUDED.state_reason,
                        entered_at=CASE
                            WHEN ng_live_runtime_state.runtime_state <> EXCLUDED.runtime_state
                            THEN now()
                            ELSE ng_live_runtime_state.entered_at
                        END,
                        updated_at=now()
                """, (
                    decision.symbol,
                    decision.strategy,
                    decision.timeframe,
                    decision.runtime_state,
                    decision.allow_new_entries,
                    decision.allow_position_management,
                    bool(active_edge),
                    bool(governance_allow),
                    market_data_fresh,
                    open_position_qty,
                    decision.reason,
                ))

                print(
                    "NG_LIVE_RUNTIME_STATE "
                    f"symbol={decision.symbol} strategy={decision.strategy} timeframe={decision.timeframe} "
                    f"state={decision.runtime_state} entries={decision.allow_new_entries} "
                    f"manage={decision.allow_position_management} active_edge={active_edge} "
                    f"governance_allow={governance_allow} fresh={market_data_fresh} "
                    f"position={open_position_qty} reason={decision.reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"NG_LIVE_RUNTIME_STATE_SUMMARY saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
