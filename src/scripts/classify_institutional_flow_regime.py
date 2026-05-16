from __future__ import annotations

import json
import os
import subprocess

from finam_core.orderflow.institutional_flow_regime import InstitutionalFlowRegimeEngine
from finam_core.storage.postgres_logger import PostgresLogger


LOAD_SQL = """
select distinct on (symbol)
    symbol,
    smart_money_score,
    rvol,
    absorption_score,
    sweep_reclaim_score,
    impulse_score,
    price_velocity,
    range_pct,
    raw_json
from smart_money_feature_events
where symbol is not null
order by symbol, ts desc
"""


INSERT_SQL = """
insert into institutional_flow_regime_events (
    symbol,
    regime,
    bias,
    confidence,
    reason,
    raw_json
)
values (%s,%s,%s,%s,%s,%s::jsonb)
"""


def main() -> int:
    pg = PostgresLogger()
    engine = InstitutionalFlowRegimeEngine()

    rows_written = 0

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(LOAD_SQL)
            rows = cur.fetchall()

            for row in rows:
                (
                    symbol,
                    smart_money_score,
                    rvol,
                    absorption_score,
                    sweep_reclaim_score,
                    impulse_score,
                    price_velocity,
                    range_pct,
                    raw_json,
                ) = row

                decision = engine.classify(
                    symbol=str(symbol),
                    smart_money_score=float(smart_money_score or 0.0),
                    rvol=float(rvol or 0.0),
                    absorption_score=float(absorption_score or 0.0),
                    sweep_reclaim_score=float(sweep_reclaim_score or 0.0),
                    impulse_score=float(impulse_score or 0.0),
                    price_velocity=float(price_velocity or 0.0),
                    range_pct=float(range_pct or 0.0),
                )

                raw = {
                    "source": "classify_institutional_flow_regime",
                    "smart_money_raw": raw_json,
                    "decision": {
                        "symbol": decision.symbol,
                        "regime": decision.regime,
                        "bias": decision.bias,
                        "confidence": decision.confidence,
                        "reason": decision.reason,
                    },
                }

                cur.execute(
                    INSERT_SQL,
                    (
                        decision.symbol,
                        decision.regime,
                        decision.bias,
                        decision.confidence,
                        decision.reason,
                        json.dumps(raw, ensure_ascii=False),
                    ),
                )
                rows_written += 1

        conn.commit()

    print(f"OK: institutional flow regimes classified rows={rows_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
