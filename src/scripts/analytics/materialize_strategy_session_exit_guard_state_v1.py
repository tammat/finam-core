#!/usr/bin/env python3
# Материализация аналитического состояния strategy_session_exit_guard_state v1.
# Pipeline не подключается. Скрипт только создаёт/обновляет таблицу guard-кандидатов.

from __future__ import annotations

import argparse
import os
import psycopg2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True)
    p.add_argument("--source", default="closed_trade_engine_v1_1")
    p.add_argument("--trade-source", default="paper")
    p.add_argument("--min-stop-trades", type=int, default=3)
    p.add_argument("--apply", action="store_true")
    return p.parse_args()


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


DDL = """
create table if not exists strategy_session_exit_guard_state (
    id bigserial primary key,
    symbol text not null,
    strategy text not null,
    timeframe text not null,
    side text not null,
    session_bucket text not null,
    source text not null,
    trade_source text not null,

    total_trades integer not null default 0,
    total_net_pnl double precision not null default 0,
    stop_trades integer not null default 0,
    stop_wins integer not null default 0,
    stop_losses integer not null default 0,
    stop_winrate double precision not null default 0,
    stop_net_pnl double precision not null default 0,
    take_trades integer not null default 0,
    take_net_pnl double precision not null default 0,

    decision text not null,
    reason text not null,
    min_stop_trades integer not null,
    generated_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique(symbol, strategy, timeframe, side, session_bucket, source, trade_source)
);

create index if not exists idx_strategy_session_exit_guard_decision
    on strategy_session_exit_guard_state(decision);

create index if not exists idx_strategy_session_exit_guard_symbol
    on strategy_session_exit_guard_state(symbol, strategy, timeframe, side, session_bucket);
"""


def decision_for(min_stop_trades, total_net_pnl, stop_trades, stop_wins, stop_net_pnl):
    if int(stop_trades or 0) >= min_stop_trades and float(stop_net_pnl or 0) < 0 and int(stop_wins or 0) == 0:
        return "BLOCK_STOP_DOMINATED", "stop_trades>=min_stop_trades_and_zero_stop_wins_and_stop_net_pnl_negative"
    if float(total_net_pnl or 0) < 0:
        return "WATCH_NEGATIVE_TOTAL", "total_net_pnl_negative"
    return "ALLOW_WATCH", "no_block_condition"


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print("=== MATERIALIZE STRATEGY SESSION EXIT GUARD STATE V1 ===")
    print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"symbols={','.join(symbols)}")
    print(f"source={args.source}")
    print(f"trade_source={args.trade_source}")
    print(f"min_stop_trades={args.min_stop_trades}")
    print()

    query = """
        with base as (
            select
              symbol,
              strategy,
              timeframe,
              side,
              coalesce(payload->'entry_payload'->>'session_bucket', 'UNKNOWN') as session_bucket,
              coalesce(payload->'exit_payload'->>'exit_reason', 'UNKNOWN') as exit_reason,
              net_pnl
            from closed_trades
            where symbol = any(%s)
              and source = %s
              and trade_source = %s
        )
        select
          symbol,
          strategy,
          timeframe,
          side,
          session_bucket,
          count(*)::int as total_trades,
          coalesce(sum(net_pnl), 0)::float8 as total_net_pnl,
          coalesce(sum(case when exit_reason = 'STOP' then 1 else 0 end), 0)::int as stop_trades,
          coalesce(sum(case when exit_reason = 'STOP' and net_pnl > 0 then 1 else 0 end), 0)::int as stop_wins,
          coalesce(sum(case when exit_reason = 'STOP' and net_pnl < 0 then 1 else 0 end), 0)::int as stop_losses,
          coalesce(sum(case when exit_reason = 'STOP' then net_pnl else 0 end), 0)::float8 as stop_net_pnl,
          coalesce(sum(case when exit_reason = 'TAKE' then 1 else 0 end), 0)::int as take_trades,
          coalesce(sum(case when exit_reason = 'TAKE' then net_pnl else 0 end), 0)::float8 as take_net_pnl
        from base
        group by symbol, strategy, timeframe, side, session_bucket
        order by stop_net_pnl asc;
    """

    upsert = """
        insert into strategy_session_exit_guard_state (
            symbol, strategy, timeframe, side, session_bucket,
            source, trade_source,
            total_trades, total_net_pnl,
            stop_trades, stop_wins, stop_losses, stop_winrate, stop_net_pnl,
            take_trades, take_net_pnl,
            decision, reason, min_stop_trades,
            generated_at, updated_at
        )
        values (
            %(symbol)s, %(strategy)s, %(timeframe)s, %(side)s, %(session_bucket)s,
            %(source)s, %(trade_source)s,
            %(total_trades)s, %(total_net_pnl)s,
            %(stop_trades)s, %(stop_wins)s, %(stop_losses)s, %(stop_winrate)s, %(stop_net_pnl)s,
            %(take_trades)s, %(take_net_pnl)s,
            %(decision)s, %(reason)s, %(min_stop_trades)s,
            now(), now()
        )
        on conflict (symbol, strategy, timeframe, side, session_bucket, source, trade_source)
        do update set
            total_trades = excluded.total_trades,
            total_net_pnl = excluded.total_net_pnl,
            stop_trades = excluded.stop_trades,
            stop_wins = excluded.stop_wins,
            stop_losses = excluded.stop_losses,
            stop_winrate = excluded.stop_winrate,
            stop_net_pnl = excluded.stop_net_pnl,
            take_trades = excluded.take_trades,
            take_net_pnl = excluded.take_net_pnl,
            decision = excluded.decision,
            reason = excluded.reason,
            min_stop_trades = excluded.min_stop_trades,
            updated_at = now();
    """

    rows_to_write = []

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(DDL)
            cur.execute(query, (symbols, args.source, args.trade_source))
            rows = cur.fetchall()

            for row in rows:
                (
                    symbol, strategy, timeframe, side, session_bucket,
                    total_trades, total_net_pnl,
                    stop_trades, stop_wins, stop_losses, stop_net_pnl,
                    take_trades, take_net_pnl
                ) = row

                stop_winrate = float(stop_wins or 0) / float(stop_trades or 1)
                decision, reason = decision_for(
                    args.min_stop_trades,
                    total_net_pnl,
                    stop_trades,
                    stop_wins,
                    stop_net_pnl,
                )

                payload = {
                    "symbol": symbol,
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "side": side,
                    "session_bucket": session_bucket,
                    "source": args.source,
                    "trade_source": args.trade_source,
                    "total_trades": total_trades,
                    "total_net_pnl": float(total_net_pnl or 0),
                    "stop_trades": stop_trades,
                    "stop_wins": stop_wins,
                    "stop_losses": stop_losses,
                    "stop_winrate": stop_winrate,
                    "stop_net_pnl": float(stop_net_pnl or 0),
                    "take_trades": take_trades,
                    "take_net_pnl": float(take_net_pnl or 0),
                    "decision": decision,
                    "reason": reason,
                    "min_stop_trades": args.min_stop_trades,
                }
                rows_to_write.append(payload)

                print(
                    f"GUARD_STATE_ROW symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"side={side} session={session_bucket} total_trades={total_trades} "
                    f"total_net_pnl={float(total_net_pnl or 0):.8f} stop_trades={stop_trades} "
                    f"stop_wins={stop_wins} stop_losses={stop_losses} stop_winrate={stop_winrate:.4f} "
                    f"stop_net_pnl={float(stop_net_pnl or 0):.8f} take_trades={take_trades} "
                    f"take_net_pnl={float(take_net_pnl or 0):.8f} decision={decision}"
                )

            if not args.apply:
                print()
                print(f"ROWS_TO_WRITE={len(rows_to_write)}")
                print("VERDICT=DRY_RUN")
                return

            for payload in rows_to_write:
                cur.execute(upsert, payload)

            c.commit()

    print()
    print(f"ROWS_WRITTEN={len(rows_to_write)}")
    print("VERDICT=APPLIED")


if __name__ == "__main__":
    main()
