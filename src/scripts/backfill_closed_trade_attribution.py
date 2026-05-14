from __future__ import annotations

import argparse
import os
import subprocess


def run_psql(sql: str) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    result = subprocess.run(
        ["psql", database_url, "-P", "pager=off", "-A", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", sql],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    limit = int(args.limit)

    preview_sql = f"""
with matched as (
    select
        ct.id as closed_trade_id,
        ct.symbol,
        s.signal_id,
        s.strategy,
        s.horizon,
        s.regime
    from closed_trades ct
    join signal_fills sf
      on sf.fill_id = ct.payload->>'entry_fill_id'
      or sf.fill_id = ct.payload->>'exit_fill_id'
    join signals s
      on s.signal_id = sf.signal_id
    where (
        coalesce(ct.strategy, '') in ('', 'UNKNOWN')
        or coalesce(ct.signal_id, '') = ''
    )
    limit {limit}
)
select *
from matched
order by closed_trade_id;
"""

    if args.dry_run:
        print(run_psql(preview_sql))
        return 0

    update_sql = f"""
with matched as (
    select distinct on (ct.id)
        ct.id as closed_trade_id,
        s.signal_id,
        s.strategy,
        s.horizon,
        s.regime
    from closed_trades ct
    join signal_fills sf
      on sf.fill_id = ct.payload->>'entry_fill_id'
      or sf.fill_id = ct.payload->>'exit_fill_id'
    join signals s
      on s.signal_id = sf.signal_id
    where (
        coalesce(ct.strategy, '') in ('', 'UNKNOWN')
        or coalesce(ct.signal_id, '') = ''
    )
    order by ct.id, s.created_at desc
    limit {limit}
)
update closed_trades ct
set
    signal_id = matched.signal_id,
    strategy = matched.strategy,
    horizon = matched.horizon,
    regime = matched.regime,
    payload = jsonb_set(
        coalesce(ct.payload, '{{}}'::jsonb),
        '{{attribution_backfill}}',
        jsonb_build_object(
            'source', 'signal_fills',
            'signal_id', matched.signal_id,
            'strategy', matched.strategy,
            'horizon', matched.horizon,
            'regime', matched.regime
        ),
        true
    )
from matched
where ct.id = matched.closed_trade_id
returning ct.id, ct.symbol, ct.signal_id, ct.strategy, ct.horizon, ct.regime;
"""
    print(run_psql(update_sql))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
