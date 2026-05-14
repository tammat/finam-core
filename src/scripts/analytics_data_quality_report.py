from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run_psql(sql: str) -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    result = subprocess.run(
        ["psql", database_url, "-P", "pager=off", "-F", "\t", "-A", "-c", sql],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def write_section(out, title: str, sql: str) -> None:
    out.write(f"\n## {title}\n")
    out.write(run_psql(sql))
    out.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="reports/analytics_data_quality_report.tsv")
    args = parser.parse_args()

    sections = {
        "SIGNALS_DATA_QUALITY": """
select
  count(*) as total_signals,
  sum(case when strategy is null or strategy = '' then 1 else 0 end) as missing_strategy,
  sum(case when regime is null or regime = '' then 1 else 0 end) as missing_regime,
  sum(case when signal_id is null or signal_id = '' then 1 else 0 end) as missing_signal_id,
  sum(case when timeframe is null or timeframe = '' then 1 else 0 end) as missing_timeframe,
  sum(case when horizon is null or horizon = '' then 1 else 0 end) as missing_horizon
from signals;
""",
        "CLOSED_TRADES_DATA_QUALITY": """
select
  count(*) as total_closed_trades,
  sum(case when strategy is null or strategy = '' or strategy = 'UNKNOWN' then 1 else 0 end) as missing_strategy,
  sum(case when regime is null or regime = '' or regime = 'UNKNOWN' then 1 else 0 end) as missing_regime,
  sum(case when signal_id is null or signal_id = '' then 1 else 0 end) as missing_signal_id,
  sum(case when trade_source is null or trade_source = '' then 1 else 0 end) as missing_trade_source
from closed_trades;
""",
        "TRADES_ORIGIN_BREAKDOWN": """
select
  coalesce(origin, 'NULL') as origin,
  coalesce(trade_source, 'NULL') as trade_source,
  count(*) as trades
from trades
group by 1,2
order by trades desc;
""",
        "INVALID_TRADE_SOURCE_VALUES": """
select
  trade_source,
  count(*) as rows_count
from trades
where trade_source like '%paperpaper%'
   or trade_source like '%unknownunknown%'
group by 1
order by rows_count desc;
""",
        "BACKFILL_VS_REAL": """
select
  case
    when origin = 'backfill_from_fills' then 'BACKFILL'
    else 'NON_BACKFILL'
  end as source_group,
  count(*) as trades
from trades
group by 1
order by trades desc;
""",
        "TOP_SYMBOLS_WITH_UNKNOWN_STRATEGY": """
select
  coalesce(symbol, 'UNKNOWN') as symbol,
  count(*) as closed_trades
from closed_trades
where strategy is null
   or strategy = ''
   or strategy = 'UNKNOWN'
group by 1
order by closed_trades desc
limit 30;
""",
        "SIGNAL_STATUS_BREAKDOWN": """
select
  coalesce(status, 'NULL') as status,
  count(*) as signals
from signals
group by 1
order by signals desc;
""",
        "RISK_EVENT_BREAKDOWN": """
select
  coalesce(event, 'NULL') as event,
  coalesce(decision, 'NULL') as decision,
  count(*) as events
from risk_events
group by 1,2
order by events desc
limit 50;
""",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out:
        out.write("ANALYTICS DATA QUALITY REPORT V1\n")
        for title, sql in sections.items():
            write_section(out, title, sql)

    print(f"OK: report written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
