from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.capital_growth_profile import CapitalGrowthProfile
from finam_core.runtime.capital_growth_daily_loss_guard import CapitalGrowthDailyLossGuard


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    profile_name = os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
    profile = CapitalGrowthProfile().load(profile_name)

    conn = psycopg2.connect(dsn)
    guard = CapitalGrowthDailyLossGuard()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    coalesce(equity, 0),
                    coalesce(realized_pnl, 0) + coalesce(unrealized_pnl, 0) as daily_pnl
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)
            row = cur.fetchone()

            if row is None:
                print("CAPITAL_GROWTH_DAILY_LOSS_GUARD_SKIP no_portfolio_snapshot", flush=True)
                return 0

            equity = float(row[0] or 0.0)
            daily_pnl = float(row[1] or 0.0)

            decision = guard.check(
                equity=equity,
                daily_pnl=daily_pnl,
                max_daily_loss_pct=profile.max_daily_loss_pct,
            )

            if not decision.allowed:
                cur.execute("""
                    create table if not exists runtime_risk_freeze (
                        id bigserial primary key,
                        created_at timestamptz not null default now(),
                        is_active boolean not null default true,
                        reason text not null,
                        raw_json jsonb not null default '{}'::jsonb
                    )
                """)

                cur.execute("""
                    insert into runtime_risk_freeze (
                        is_active,
                        reason,
                        raw_json
                    )
                    values (
                        true,
                        %s,
                        jsonb_build_object(
                            'guard', 'capital_growth_daily_loss_guard_v1',
                            'profile', %s,
                            'daily_pnl', %s,
                            'daily_loss_pct', %s,
                            'limit_pct', %s
                        )
                    )
                """, (
                    f"capital_growth_daily_loss_guard:{decision.reason}",
                    profile.profile,
                    decision.daily_pnl,
                    decision.daily_loss_pct,
                    decision.limit_pct,
                ))

                print(
                    "CAPITAL_GROWTH_DAILY_LOSS_GUARD_BLOCK "
                    f"profile={profile.profile} "
                    f"daily_pnl={decision.daily_pnl} "
                    f"daily_loss_pct={decision.daily_loss_pct:.4f} "
                    f"limit={decision.limit_pct:.4f} "
                    f"freeze=1",
                    flush=True,
                )
                return 1

            print(
                "CAPITAL_GROWTH_DAILY_LOSS_GUARD_OK "
                f"profile={profile.profile} "
                f"daily_pnl={decision.daily_pnl} "
                f"daily_loss_pct={decision.daily_loss_pct:.4f} "
                f"limit={decision.limit_pct:.4f}",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
