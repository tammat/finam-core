#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


DDL = """
create table if not exists guard_candidate_classification_state (
    id bigserial primary key,
    symbol text not null,
    strategy text not null,
    timeframe text not null,
    side text not null,
    session_bucket text not null,

    decision text not null,
    classification text not null,
    reason text not null,

    total_trades integer not null default 0,
    total_net_pnl double precision not null default 0,
    expectancy double precision not null default 0,
    stop_trades integer not null default 0,
    stop_rate double precision not null default 0,
    stop_net_pnl double precision not null default 0,
    take_trades integer not null default 0,
    take_rate double precision not null default 0,
    take_net_pnl double precision not null default 0,
    pf_proxy double precision,

    source text not null default 'guard_candidate_classification_v1',
    generated_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique(symbol, strategy, timeframe, side, session_bucket, source)
);

create index if not exists idx_guard_candidate_classification_class
    on guard_candidate_classification_state(classification);

create index if not exists idx_guard_candidate_classification_symbol
    on guard_candidate_classification_state(symbol, strategy, timeframe, side, session_bucket);
"""


def classify(row):
    (
        symbol, strategy, timeframe, side, session, decision,
        total_trades, total_net_pnl, expectancy,
        stop_trades, stop_net_pnl, take_trades, take_net_pnl,
        stop_rate, take_rate, pf
    ) = row

    total_trades = int(total_trades or 0)
    total_net_pnl = float(total_net_pnl or 0)
    expectancy = float(expectancy or 0)
    stop_rate = float(stop_rate or 0)
    take_rate = float(take_rate or 0)
    pf_value = None if pf is None else float(pf)

    # Жёсткий блок: отрицательный результат, плохая математика или явная stop-доминация.
    if symbol.startswith("BR") and total_net_pnl < 0 and total_trades >= 3:
        return "BLOCK_READY", "br_negative_total_without_exit_attribution"

    if decision == "BLOCK_STOP_DOMINATED":
        if pf_value is not None and pf_value >= 0.90 and total_net_pnl > -0.003:
            return "RESEARCH_ONLY", "near_breakeven_stop_dominated_candidate"
        if total_trades >= 3 and stop_rate >= 0.75 and total_net_pnl < 0:
            return "BLOCK_READY", "high_stop_rate_negative_expectancy"
        if total_trades >= 3 and take_rate == 0 and total_net_pnl < 0:
            return "BLOCK_READY", "no_take_profit_negative_expectancy"
        return "RESEARCH_ONLY", "stop_dominated_but_requires_more_research"

    if decision == "WATCH_NEGATIVE_TOTAL":
        if total_trades >= 3 and total_net_pnl < 0:
            return "RESEARCH_ONLY", "negative_total_watch_requires_research"
        return "RESEARCH_ONLY", "watch_negative_low_sample"

    if decision == "ALLOW_WATCH":
        if total_net_pnl >= 0 and expectancy >= 0:
            return "KEEP_WATCH", "positive_or_flat_allow_watch"
        return "RESEARCH_ONLY", "allow_watch_but_not_positive"

    return "RESEARCH_ONLY", "fallback_classification"


def main():
    source = "guard_candidate_classification_v1"

    sql = """
        select
            symbol,
            strategy,
            timeframe,
            side,
            session_bucket,
            decision,
            total_trades,
            total_net_pnl,
            total_net_pnl / nullif(total_trades, 0) as expectancy,
            stop_trades,
            stop_net_pnl,
            take_trades,
            take_net_pnl,
            stop_trades::float8 / nullif(total_trades, 0) as stop_rate,
            take_trades::float8 / nullif(total_trades, 0) as take_rate,
            case
                when abs(stop_net_pnl) > 0 then take_net_pnl / abs(stop_net_pnl)
                else null
            end as pf_proxy
        from strategy_session_exit_guard_state
    """

    upsert = """
        insert into guard_candidate_classification_state (
            symbol, strategy, timeframe, side, session_bucket,
            decision, classification, reason,
            total_trades, total_net_pnl, expectancy,
            stop_trades, stop_rate, stop_net_pnl,
            take_trades, take_rate, take_net_pnl,
            pf_proxy, source, generated_at, updated_at
        )
        values (
            %(symbol)s, %(strategy)s, %(timeframe)s, %(side)s, %(session_bucket)s,
            %(decision)s, %(classification)s, %(reason)s,
            %(total_trades)s, %(total_net_pnl)s, %(expectancy)s,
            %(stop_trades)s, %(stop_rate)s, %(stop_net_pnl)s,
            %(take_trades)s, %(take_rate)s, %(take_net_pnl)s,
            %(pf_proxy)s, %(source)s, now(), now()
        )
        on conflict (symbol, strategy, timeframe, side, session_bucket, source)
        do update set
            decision = excluded.decision,
            classification = excluded.classification,
            reason = excluded.reason,
            total_trades = excluded.total_trades,
            total_net_pnl = excluded.total_net_pnl,
            expectancy = excluded.expectancy,
            stop_trades = excluded.stop_trades,
            stop_rate = excluded.stop_rate,
            stop_net_pnl = excluded.stop_net_pnl,
            take_trades = excluded.take_trades,
            take_rate = excluded.take_rate,
            take_net_pnl = excluded.take_net_pnl,
            pf_proxy = excluded.pf_proxy,
            updated_at = now()
    """

    print("=== MATERIALIZE GUARD CANDIDATE CLASSIFICATION V1 ===")

    payloads = []

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(DDL)
            cur.execute(sql)
            rows = cur.fetchall()

            for row in rows:
                (
                    symbol, strategy, timeframe, side, session, decision,
                    total_trades, total_net_pnl, expectancy,
                    stop_trades, stop_net_pnl, take_trades, take_net_pnl,
                    stop_rate, take_rate, pf
                ) = row

                classification, reason = classify(row)

                payload = {
                    "symbol": symbol,
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "side": side,
                    "session_bucket": session,
                    "decision": decision,
                    "classification": classification,
                    "reason": reason,
                    "total_trades": int(total_trades or 0),
                    "total_net_pnl": float(total_net_pnl or 0),
                    "expectancy": float(expectancy or 0),
                    "stop_trades": int(stop_trades or 0),
                    "stop_rate": float(stop_rate or 0),
                    "stop_net_pnl": float(stop_net_pnl or 0),
                    "take_trades": int(take_trades or 0),
                    "take_rate": float(take_rate or 0),
                    "take_net_pnl": float(take_net_pnl or 0),
                    "pf_proxy": None if pf is None else float(pf),
                    "source": source,
                }
                payloads.append(payload)

                cur.execute(upsert, payload)

                print(
                    f"CLASS_ROW symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"side={side} session={session} decision={decision} "
                    f"classification={classification} reason={reason} "
                    f"trades={int(total_trades or 0)} net_pnl={float(total_net_pnl or 0):.8f} "
                    f"expectancy={float(expectancy or 0):.8f} "
                    f"stop_rate={float(stop_rate or 0):.4f} take_rate={float(take_rate or 0):.4f} "
                    f"pf_proxy={None if pf is None else round(float(pf), 4)}"
                )

            c.commit()

    summary = {}
    for p in payloads:
        summary[p["classification"]] = summary.get(p["classification"], 0) + 1

    print()
    for k in sorted(summary):
        print(f"SUMMARY classification={k} rows={summary[k]}")

    print(f"ROWS_WRITTEN={len(payloads)}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
