from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.capital_growth_profile import CapitalGrowthProfile
from finam_core.runtime.capital_growth_portfolio_governor import (
    CapitalGrowthPortfolioGovernor,
)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    profile = CapitalGrowthProfile().load(
        os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
    )

    conn = psycopg2.connect(dsn)
    governor = CapitalGrowthPortfolioGovernor()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select count(*)
                from execution_intents
                where intent_state in ('SENT','ACK','PARTIAL_FILL','FILLED')
                  and coalesce(raw_json->>'capital_growth_mode','') <> ''
            """)
            active_growth_trades = int(cur.fetchone()[0] or 0)

            decision = governor.check(
                active_growth_trades=active_growth_trades,
                max_active_growth_trades=profile.max_active_growth_trades,
            )

            print(
                "CAPITAL_GROWTH_PORTFOLIO_GOVERNOR "
                f"profile={profile.profile} "
                f"allowed={decision.allowed} "
                f"active={decision.active_growth_trades} "
                f"limit={decision.max_active_growth_trades} "
                f"reason={decision.reason}",
                flush=True,
            )

            return 0 if decision.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
