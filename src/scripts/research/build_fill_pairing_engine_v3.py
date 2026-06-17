#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict, deque
from dataclasses import dataclass
from decimal import Decimal

import psycopg2
import psycopg2.extras


DDL = """
create table if not exists closed_trade_chains_v3 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    entry_trade_id bigint not null,
    exit_trade_id bigint not null,

    entry_fill_id text,
    exit_fill_id text,

    entry_ts timestamptz not null,
    exit_ts timestamptz not null,

    side text not null,
    qty numeric not null,

    entry_price numeric not null,
    exit_price numeric not null,

    gross_pnl numeric not null,
    net_pnl numeric not null,

    quality_status text not null,
    quality_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(entry_trade_id, exit_trade_id, symbol, strategy, timeframe, trade_source)
);
"""


TRUNCATE = """
truncate table trade_attribution_v3, closed_trade_chains_v3;
"""


FILL_SQL = """
select
    t.id,
    t.symbol,
    t.strategy,
    t.timeframe,
    t.trade_source,
    t.side,
    t.qty,
    t.price,
    t.commission,
    t.fill_id,
    t.created_at,
    coalesce(nullif(t.origin,''),'paper') as origin
from trades t
join rebuild_candidates_v1 c
  on c.symbol=t.symbol
 and c.strategy=t.strategy
 and c.timeframe=t.timeframe
 and c.trade_source=t.trade_source
where c.rebuild_status='PLANNED'
  and coalesce(t.strategy,'') <> ''
  and coalesce(t.timeframe,'') <> ''
  and coalesce(t.is_invalid,false)=false
  and (coalesce(t.origin,'') = 'paper' or (coalesce(t.origin,'') = '' and t.trade_source = 'paper'))
order by
    t.symbol,
    t.strategy,
    t.timeframe,
    t.trade_source,
    t.created_at,
    t.id;
"""

INSERT = """
insert into closed_trade_chains_v3 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    entry_trade_id,
    exit_trade_id,
    entry_fill_id,
    exit_fill_id,
    entry_ts,
    exit_ts,
    side,
    qty,
    entry_price,
    exit_price,
    gross_pnl,
    net_pnl,
    quality_status,
    quality_reason,
    runtime_allowed,
    execution_enabled
)
values (
    %(symbol)s,
    %(strategy)s,
    %(timeframe)s,
    %(trade_source)s,
    %(entry_trade_id)s,
    %(exit_trade_id)s,
    %(entry_fill_id)s,
    %(exit_fill_id)s,
    %(entry_ts)s,
    %(exit_ts)s,
    %(side)s,
    %(qty)s,
    %(entry_price)s,
    %(exit_price)s,
    %(gross_pnl)s,
    %(net_pnl)s,
    %(quality_status)s,
    %(quality_reason)s,
    false,
    false
)
on conflict do nothing;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    count(*) as chains,
    count(*) filter (where quality_status='FULL') as full_chains,
    count(*) filter (where quality_status='PARTIAL') as partial_chains,
    count(distinct entry_ts::date) as entry_days,
    count(distinct exit_ts::date) as exit_days,
    coalesce(sum(net_pnl),0) as net_pnl
from closed_trade_chains_v3
group by symbol,strategy,timeframe,trade_source
order by symbol,strategy,timeframe;
"""


@dataclass
class Fill:
    id: int
    symbol: str
    strategy: str
    timeframe: str
    trade_source: str
    side: str
    qty: Decimal
    price: Decimal
    commission: Decimal
    fill_id: str | None
    created_at: object
    origin: str


def as_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def opposite(side: str) -> str:
    return "SELL" if side == "BUY" else "BUY"


def pnl(entry: Fill, exit_: Fill, qty: Decimal) -> Decimal:
    if entry.side == "BUY" and exit_.side == "SELL":
        return (exit_.price - entry.price) * qty
    if entry.side == "SELL" and exit_.side == "BUY":
        return (entry.price - exit_.price) * qty
    return Decimal("0")


def quality(entry: Fill, exit_: Fill) -> tuple[str, str]:
    if not entry.strategy or not entry.timeframe:
        return "PARTIAL", "missing_entry_strategy_or_timeframe"
    if not exit_.strategy or not exit_.timeframe:
        return "PARTIAL", "missing_exit_strategy_or_timeframe"
    if entry.strategy != exit_.strategy or entry.timeframe != exit_.timeframe:
        return "PARTIAL", "strategy_timeframe_mismatch"
    if entry.origin == "backfill_from_fills" or exit_.origin == "backfill_from_fills":
        return "PARTIAL", "contains_backfill_fill"
    return "FULL", "exact_fill_pair"


def should_skip_chain(entry: Fill, exit_: Fill) -> tuple[bool, str]:
    """
    Русский комментарий:
    Жёсткий фильтр качества V3-цепочек.
    Для USDRUBF intraday M5 не допускаем цепочки длиннее 120 минут,
    чтобы gap/backfill-артефакты не попадали в clean V3 статистику.
    """
    if (
        entry.symbol == "USDRUBF@RTSX"
        and entry.strategy == "USD_INTRADAY_REGIME"
        and entry.timeframe == "M5"
    ):
        duration = exit_.created_at - entry.created_at
        if duration.total_seconds() > 120 * 60:
            return True, "usd_intraday_duration_exceeded"

    return False, ""


def main() -> int:
    print("=== FILL PAIRING ENGINE V3 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(FILL_SQL)
            rows = cur.fetchall()

            queues: dict[tuple[str, str, str, str, str], deque[Fill]] = defaultdict(deque)
            inserted = 0
            skipped_same_side = 0
            skipped_burst_chains = 0

            # FILL_PAIRING_ENGINE_V3_BURST_SKIP:
            # Русский комментарий:
            # Не даём burst-кластерам попасть в closed_trade_chains_v3.
            # Цепочки, возникающие пакетно внутри одной минуты, считаются research artifact.
            max_chains_per_minute = 10
            chains_per_minute = defaultdict(int)

            for r in rows:
                fill = Fill(
                    id=int(r["id"]),
                    symbol=r["symbol"],
                    strategy=r["strategy"],
                    timeframe=r["timeframe"],
                    trade_source=r["trade_source"],
                    side=r["side"],
                    qty=as_decimal(r["qty"]),
                    price=as_decimal(r["price"]),
                    commission=as_decimal(r["commission"]),
                    fill_id=r["fill_id"],
                    created_at=r["created_at"],
                    origin=r["origin"],
                )

                key = (
                    fill.symbol,
                    fill.strategy,
                    fill.timeframe,
                    fill.trade_source,
                    opposite(fill.side),
                )

                own_key = (
                    fill.symbol,
                    fill.strategy,
                    fill.timeframe,
                    fill.trade_source,
                    fill.side,
                )

                remaining_qty = fill.qty

                while remaining_qty > 0 and queues[key]:
                    entry = queues[key][0]
                    matched_qty = min(entry.qty, remaining_qty)

                    skip_chain, skip_reason = should_skip_chain(entry, fill)
                    if skip_chain:
                        skipped_burst_chains += 1
                        print(
                            "FILL_PAIRING_V3_SKIP_CHAIN",
                            f"symbol={entry.symbol}",
                            f"strategy={entry.strategy}",
                            f"timeframe={entry.timeframe}",
                            f"entry_trade_id={entry.id}",
                            f"exit_trade_id={fill.id}",
                            f"reason={skip_reason}",
                            "runtime_allow=0",
                            "execution_enabled=0",
                            flush=True,
                        )

                        # Русский комментарий: загрязнённая цепочка не вставляется в closed_trade_chains_v3.
                        # Exit считается использованным, чтобы не подцепить его к другой старой позиции.
                        entry.qty -= matched_qty
                        remaining_qty -= matched_qty

                        if entry.qty <= 0:
                            queues[key].popleft()

                        continue

                    gross = pnl(entry, fill, matched_qty)
                    net = gross - entry.commission - fill.commission
                    q_status, q_reason = quality(entry, fill)

                    minute_key = (
                        fill.symbol,
                        fill.strategy,
                        fill.timeframe,
                        fill.trade_source,
                        entry.created_at.replace(second=0, microsecond=0),
                    )

                    if chains_per_minute[minute_key] >= max_chains_per_minute:
                        skipped_burst_chains += 1
                        entry.qty -= matched_qty
                        remaining_qty -= matched_qty

                        if entry.qty <= 0:
                            queues[key].popleft()

                        continue

                    chains_per_minute[minute_key] += 1

                    payload = {
                        "symbol": fill.symbol,
                        "strategy": fill.strategy,
                        "timeframe": fill.timeframe,
                        "trade_source": fill.trade_source,
                        "entry_trade_id": entry.id,
                        "exit_trade_id": fill.id,
                        "entry_fill_id": entry.fill_id,
                        "exit_fill_id": fill.fill_id,
                        "entry_ts": entry.created_at,
                        "exit_ts": fill.created_at,
                        "side": entry.side,
                        "qty": matched_qty,
                        "entry_price": entry.price,
                        "exit_price": fill.price,
                        "gross_pnl": gross,
                        "net_pnl": net,
                        "quality_status": q_status,
                        "quality_reason": q_reason,
                    }

                    cur.execute(INSERT, payload)
                    inserted += 1

                    entry.qty -= matched_qty
                    remaining_qty -= matched_qty

                    if entry.qty <= 0:
                        queues[key].popleft()

                if remaining_qty > 0:
                    fill.qty = remaining_qty
                    queues[own_key].append(fill)
                else:
                    skipped_same_side += 1

            cur.execute(REPORT)
            report = cur.fetchall()

        conn.commit()

    for r in report:
        print(
            "FILL_PAIRING_V3_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"chains={r['chains']} "
            f"full={r['full_chains']} "
            f"partial={r['partial_chains']} "
            f"entry_days={r['entry_days']} "
            f"exit_days={r['exit_days']} "
            f"net_pnl={float(r['net_pnl'] or 0):.6f} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "FILL_PAIRING_ENGINE_V3_SUMMARY "
        f"fills_loaded={len(rows)} "
        f"chains_inserted={inserted} "
        f"same_side_closed={skipped_same_side} "
        f"skipped_burst_chains={skipped_burst_chains} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("FILL_PAIRING_ENGINE_V3_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
