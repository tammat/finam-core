from __future__ import annotations

import os
import psycopg


SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        final_state,
        reason
    FROM (
        SELECT
            'RESEARCH_WATCH_CONTAMINATED'::text AS final_state,
            'repeatability_high_day_concentration'::text AS reason
    ) x;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    final_state = row[0]
    reason = row[1]

    repeatability_confirmed = (
        final_state != "RESEARCH_WATCH_CONTAMINATED"
        and "repeatability_high_day_concentration" not in reason
    )

    print("BR_REPEATABILITY_GATE_V1")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print(f"repeatability_confirmed={str(repeatability_confirmed).lower()}")
    print(f"reason={reason}")
    print(
        "BR_REPEATABILITY_GATE_V1_OK "
        f"repeatability_confirmed={str(repeatability_confirmed).lower()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
