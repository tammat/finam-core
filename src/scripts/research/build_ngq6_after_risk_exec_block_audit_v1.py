#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass

import psycopg2
import psycopg2.extras


@dataclass
class StageCounts:
    handler_allowed: int = 0
    smart_entries: int = 0
    quality_allow: int = 0
    quality_block: int = 0
    paper_bypass: int = 0
    risk_ctx: int = 0
    risk_ok_after_ngq6: int = 0
    after_risk_ok: int = 0
    before_portfolio_gate: int = 0
    portfolio_risk_ok_after_ngq6: int = 0
    portfolio_heat_ok_after_ngq6: int = 0
    cluster_block_after_portfolio: int = 0
    trade_exec: int = 0
    fills: int = 0
    risk_reject: int = 0
    trade_limit_symbol: int = 0
    trade_limit_global: int = 0
    position_block: int = 0
    cooldown_block: int = 0


def run_journalctl(since: str) -> list[str]:
    cmd = [
        "journalctl",
        "-u",
        "finam-paper-pipeline.service",
        "--since",
        since,
        "--no-pager",
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode not in (0, 1):
        print(f"JOURNALCTL_WARNING returncode={proc.returncode} stderr={proc.stderr.strip()}")
    return proc.stdout.splitlines()


def count_stages(lines: list[str]) -> StageCounts:
    counts = StageCounts()

    pending_after_portfolio = False
    pending_ttl = 0

    for line in lines:
        is_ngq6 = "NGQ6@RTSX" in line

        if "PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1" in line and "allowed=True" in line:
            counts.handler_allowed += 1

        if "PIPE_SMART_ENTRY" in line and "symbol=NGQ6@RTSX" in line:
            counts.smart_entries += 1

        if "PIPE_NG_SMART_ENTRY_QUALITY_GATE_V1" in line and "symbol=NGQ6@RTSX" in line and "allowed=1" in line:
            counts.quality_allow += 1

        if "PIPE_NG_SMART_ENTRY_QUALITY_BLOCK_V1" in line and "symbol=NGQ6@RTSX" in line:
            counts.quality_block += 1

        if "NG_PAPER_ACCUMULATION_BYPASS" in line and "symbol=NGQ6@RTSX" in line:
            counts.paper_bypass += 1

        if "PIPE_RISK_CTX" in line and "symbol=NGQ6@RTSX" in line:
            counts.risk_ctx += 1

        if "PIPE_NG_EXEC_TRACE_AFTER_RISK_OK" in line and "symbol=NGQ6@RTSX" in line:
            counts.after_risk_ok += 1

        if "PIPE_NG_EXEC_TRACE_BEFORE_PORTFOLIO_GATE" in line and "symbol=NGQ6@RTSX" in line:
            counts.before_portfolio_gate += 1
            pending_after_portfolio = True
            pending_ttl = 20

        if pending_after_portfolio:
            if "PIPE_PORTFOLIO_RISK_OK" in line:
                counts.portfolio_risk_ok_after_ngq6 += 1

            if "PIPE_PORTFOLIO_HEAT_OK" in line:
                counts.portfolio_heat_ok_after_ngq6 += 1

            if "PIPE_CLUSTER_BLOCK" in line:
                counts.cluster_block_after_portfolio += 1
                pending_after_portfolio = False
                pending_ttl = 0

            if "PIPE_TRADE_EXEC" in line and "symbol=NGQ6@RTSX" in line:
                counts.trade_exec += 1
                pending_after_portfolio = False
                pending_ttl = 0

            if "PIPE_FILLED paper NGQ6@RTSX" in line:
                counts.fills += 1
                pending_after_portfolio = False
                pending_ttl = 0

            if "PIPE_RISK_REJECT" in line:
                counts.risk_reject += 1
                pending_after_portfolio = False
                pending_ttl = 0

            if "PIPE_TRADE_LIMIT_BLOCK_SYMBOL NGQ6@RTSX" in line:
                counts.trade_limit_symbol += 1
                pending_after_portfolio = False
                pending_ttl = 0

            if "PIPE_TRADE_LIMIT_BLOCK_GLOBAL" in line:
                counts.trade_limit_global += 1

            if "PIPE_POSITION_BLOCK" in line:
                counts.position_block += 1
                pending_after_portfolio = False
                pending_ttl = 0

            if "PIPE_COOLDOWN_BLOCK" in line:
                counts.cooldown_block += 1
                pending_after_portfolio = False
                pending_ttl = 0

            pending_ttl -= 1
            if pending_ttl <= 0:
                pending_after_portfolio = False
                pending_ttl = 0

        if "PIPE_TRADE_EXEC" in line and "symbol=NGQ6@RTSX" in line:
            counts.trade_exec += 1

        if "PIPE_FILLED paper NGQ6@RTSX" in line:
            counts.fills += 1

    return counts


def db_snapshot(window: str) -> dict:
    dsn = os.environ["DATABASE_URL"]

    sql_trades = """
    select
        count(*) as recent_trades,
        max(created_at) as last_trade_ts
    from trades
    where symbol='NGQ6@RTSX'
      and created_at >= now() - %s::interval;
    """

    sql_v3 = """
    select
        symbol,
        strategy,
        timeframe,
        clean_trades,
        trade_days,
        v3_full_chains,
        round(v3_net_pnl,6) as pnl,
        accumulation_status
    from clean_paper_accumulation_tracker_v1
    where symbol='NGQ6@RTSX'
    order by strategy,timeframe;
    """

    sql_universe = """
    select
        symbol,
        strategy,
        timeframe,
        priority,
        is_enabled,
        source,
        updated_at
    from runtime_active_universe
    where symbol='NGQ6@RTSX'
    order by updated_at desc;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_trades, (window,))
            trades = cur.fetchone()

            cur.execute(sql_v3)
            v3_rows = cur.fetchall()

            cur.execute(sql_universe)
            universe_rows = cur.fetchall()

    return {
        "trades": trades,
        "v3_rows": v3_rows,
        "universe_rows": universe_rows,
    }


def verdict(c: StageCounts, recent_trades: int) -> str:
    if c.handler_allowed == 0:
        return "NO_HANDLER_ROUTE"
    if c.smart_entries == 0:
        return "NO_SMART_ENTRY"
    if c.quality_allow == 0 and c.quality_block > 0:
        return "QUALITY_GATE_BLOCK"
    if c.after_risk_ok > 0 and c.before_portfolio_gate > 0 and c.cluster_block_after_portfolio > 0 and c.trade_exec == 0:
        return "CLUSTER_BLOCK_AFTER_PORTFOLIO_GATE"
    if c.after_risk_ok > 0 and c.before_portfolio_gate > 0 and c.trade_exec == 0:
        return "AFTER_RISK_BEFORE_EXEC_BLOCK_UNKNOWN"
    if c.trade_exec > 0 and c.fills == 0:
        return "TRADE_EXEC_WITHOUT_FILL"
    if c.fills > 0 and recent_trades == 0:
        return "FILL_NOT_PERSISTED"
    if recent_trades > 0:
        return "NGQ6_FORWARD_TRADES_OK"
    return "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="60 minutes ago")
    parser.add_argument("--window", default="60 minutes")
    args = parser.parse_args()

    print("=== NGQ6 AFTER RISK EXEC BLOCK AUDIT V1 ===")
    print("mode=diagnostic")
    print(f"since={args.since}")
    print(f"window={args.window}")
    print("runtime_allow=0")
    print("execution_enabled=0")

    lines = run_journalctl(args.since)
    counts = count_stages(lines)
    snapshot = db_snapshot(args.window)

    trades = snapshot["trades"]
    recent_trades = int(trades["recent_trades"] or 0)

    print()
    print("STAGE_COUNTS")
    for field in counts.__dataclass_fields__:
        print(f"{field}={getattr(counts, field)}")

    print()
    print(
        "DB_RECENT_TRADES "
        f"recent_trades={recent_trades} "
        f"last_trade_ts={trades['last_trade_ts']}"
    )

    print()
    print("RUNTIME_ACTIVE_UNIVERSE")
    for r in snapshot["universe_rows"]:
        print(
            "RUNTIME_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"priority={r['priority']} "
            f"is_enabled={r['is_enabled']} "
            f"source={r['source']} "
            f"updated_at={r['updated_at']}"
        )

    print()
    print("CLEAN_V3_NGQ6")
    for r in snapshot["v3_rows"]:
        print(
            "V3_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"clean_trades={r['clean_trades']} "
            f"trade_days={r['trade_days']} "
            f"v3_full_chains={r['v3_full_chains']} "
            f"pnl={r['pnl']} "
            f"status={r['accumulation_status']}"
        )

    final_verdict = verdict(counts, recent_trades)
    print()
    print(f"VERDICT={final_verdict}")
    print("NGQ6_AFTER_RISK_EXEC_BLOCK_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
