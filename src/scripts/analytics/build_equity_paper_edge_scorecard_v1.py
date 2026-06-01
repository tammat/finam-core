from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_SYMBOLS = ["PLZL@MISX", "LKOH@MISX", "SBER@MISX"]


SQL = """
with ordered as (
    select
        id,
        symbol,
        side,
        price,
        qty,
        coalesce(commission, 0) as commission,
        created_at,
        row_number() over (
            partition by symbol, side
            order by created_at, id
        ) as side_seq
    from trades
    where symbol = any(%(symbols)s)
      and origin = 'paper'
      and is_invalid = false
      and side in ('BUY', 'SELL')
),
pairs as (
    select
        b.symbol,
        b.side_seq,
        b.created_at as entry_ts,
        s.created_at as exit_ts,
        b.price as entry_price,
        s.price as exit_price,
        least(b.qty, s.qty) as qty,
        (s.price - b.price) * least(b.qty, s.qty)
          - b.commission
          - s.commission as pnl
    from ordered b
    join ordered s
      on s.symbol = b.symbol
     and s.side_seq = b.side_seq
    where b.side = 'BUY'
      and s.side = 'SELL'
),
stats as (
    select
        symbol,
        count(*)::int as round_trips,
        min(entry_ts) as first_entry,
        max(exit_ts) as last_exit,
        round(sum(pnl)::numeric, 6) as total_pnl,
        round(avg(pnl)::numeric, 6) as expectancy,
        count(*) filter (where pnl > 0)::int as wins,
        count(*) filter (where pnl < 0)::int as losses,
        round(
            (
                count(*) filter (where pnl > 0)::numeric
                / nullif(count(*), 0)
            ),
            6
        ) as winrate,
        round(avg(pnl) filter (where pnl > 0)::numeric, 6) as avg_win,
        round(avg(abs(pnl)) filter (where pnl < 0)::numeric, 6) as avg_loss,
        round(
            (
                sum(pnl) filter (where pnl > 0)
                / nullif(abs(sum(pnl) filter (where pnl < 0)), 0)
            )::numeric,
            6
        ) as profit_factor
    from pairs
    group by symbol
)
select *
from stats
order by profit_factor desc nulls last, expectancy desc;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def parse_symbols(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_SYMBOLS
    return [item.strip() for item in value.split(",") if item.strip()]


def f(value) -> float:
    return 0.0 if value is None else float(value)


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def recommendation(round_trips: int, expectancy: float, pf: float) -> str:
    if round_trips >= 300 and expectancy > 0 and pf >= 1.10:
        return "PRIMARY_CANDIDATE"
    if round_trips >= 100 and expectancy > 0 and pf >= 1.05:
        return "WATCH_POSITIVE"
    if round_trips >= 100 and expectancy <= 0:
        return "REJECT_GLOBAL_EDGE"
    return "INSUFFICIENT_OR_WEAK"


def reason(rec: str) -> str:
    if rec == "PRIMARY_CANDIDATE":
        return "large_sample_positive_edge"
    if rec == "WATCH_POSITIVE":
        return "positive_but_marginal_edge"
    if rec == "REJECT_GLOBAL_EDGE":
        return "negative_global_expectancy"
    return "sample_or_edge_insufficient"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols)

    print("EQUITY_PAPER_EDGE_SCORECARD_V1", flush=True)
    print(
        "EQUITY_EDGE_CONFIG",
        f"git_clean={git_clean()}",
        f"symbols={','.join(symbols)}",
        "source=trades",
        "origin=paper",
        "pairing=BUY_TO_NEXT_SELL_BY_SYMBOL_SEQUENCE",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL, {"symbols": symbols})
            rows = [dict(row) for row in cur.fetchall()]

    primary = 0
    watch = 0
    rejected = 0

    for row in rows:
        rt = int(row.get("round_trips") or 0)
        exp = f(row.get("expectancy"))
        pf = f(row.get("profit_factor"))
        rec = recommendation(rt, exp, pf)

        if rec == "PRIMARY_CANDIDATE":
            primary += 1
        elif rec == "WATCH_POSITIVE":
            watch += 1
        elif rec == "REJECT_GLOBAL_EDGE":
            rejected += 1

        print(
            "EQUITY_EDGE_ROW",
            f"symbol={row.get('symbol')}",
            f"round_trips={rt}",
            f"wins={row.get('wins')}",
            f"losses={row.get('losses')}",
            f"winrate={row.get('winrate')}",
            f"expectancy={row.get('expectancy')}",
            f"total_pnl={row.get('total_pnl')}",
            f"avg_win={fmt(row.get('avg_win'))}",
            f"avg_loss={fmt(row.get('avg_loss'))}",
            f"profit_factor={fmt(row.get('profit_factor'))}",
            f"first_entry={row.get('first_entry')}",
            f"last_exit={row.get('last_exit')}",
            f"recommendation={rec}",
            f"reason={reason(rec)}",
            flush=True,
        )

    print(
        "EQUITY_EDGE_SUMMARY",
        f"rows={len(rows)}",
        f"primary={primary}",
        f"watch={watch}",
        f"rejected={rejected}",
        flush=True,
    )

    print("EQUITY_PAPER_EDGE_SCORECARD_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
