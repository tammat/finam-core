#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import psycopg2
import psycopg2.extras


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return proc.stdout or ""


def main() -> int:
    print("=== NGQ6 PAPER CLUSTER BLOCK ADVISORY V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    env_raw = run([
        "systemctl",
        "show",
        "finam-paper-pipeline.service",
        "-p",
        "Environment",
        "--no-pager",
    ])

    env_flat = env_raw.replace("Environment=", "").replace(" ", "\n")

    bypass_enabled = "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1=1" in env_flat
    symbols_line = ""
    for line in env_flat.splitlines():
        if line.startswith("PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS="):
            symbols_line = line

    ngq6_in_symbols = "NGQ6@RTSX" in symbols_line

    print(f"ENV_BYPASS_ENABLED={int(bypass_enabled)}")
    print(f"ENV_SYMBOLS_LINE={symbols_line}")
    print(f"ENV_NGQ6_ALLOWED={int(ngq6_in_symbols)}")

    journal = run([
        "journalctl",
        "-u",
        "finam-paper-pipeline.service",
        "--since",
        "60 minutes ago",
        "--no-pager",
    ])

    lines = journal.splitlines()

    ngq6_cluster_blocks = sum(
        1 for x in lines
        if "PIPE_CLUSTER_BLOCK" in x and "NGQ6@RTSX" in x
    )

    ngq6_cluster_advisory = sum(
        1 for x in lines
        if "PIPE_CLUSTER_BLOCK_ADVISORY_CONTINUE" in x and "symbol=NGQ6@RTSX" in x
    )

    ngq6_trade_exec = sum(
        1 for x in lines
        if "PIPE_TRADE_EXEC symbol=NGQ6@RTSX" in x
    )

    ngq6_fills = sum(
        1 for x in lines
        if "PIPE_FILLED paper NGQ6@RTSX" in x
    )

    print(f"LOG_NGQ6_CLUSTER_BLOCKS={ngq6_cluster_blocks}")
    print(f"LOG_NGQ6_CLUSTER_ADVISORY={ngq6_cluster_advisory}")
    print(f"LOG_NGQ6_TRADE_EXEC={ngq6_trade_exec}")
    print(f"LOG_NGQ6_FILLS={ngq6_fills}")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select count(*) as trades, max(created_at) as last_trade
                from trades
                where symbol='NGQ6@RTSX'
                  and created_at >= now() - interval '60 minutes';
            """)
            trades = cur.fetchone()

            cur.execute("""
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
            """)
            v3_rows = cur.fetchall()

    print(
        "DB_NGQ6_RECENT_TRADES "
        f"trades={int(trades['trades'] or 0)} "
        f"last_trade={trades['last_trade']}"
    )

    for r in v3_rows:
        print(
            "DB_NGQ6_V3_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"clean_trades={r['clean_trades']} "
            f"trade_days={r['trade_days']} "
            f"v3_full_chains={r['v3_full_chains']} "
            f"pnl={r['pnl']} "
            f"status={r['accumulation_status']}"
        )

    if not bypass_enabled:
        print("VERDICT=CLUSTER_BYPASS_ENV_DISABLED")
    elif not ngq6_in_symbols:
        print("VERDICT=NGQ6_NOT_IN_CLUSTER_BYPASS_SYMBOLS")
    elif ngq6_cluster_advisory > 0 and ngq6_trade_exec == 0:
        print("VERDICT=CLUSTER_ADVISORY_OK_NEXT_BLOCK_AFTER_CLUSTER")
    elif ngq6_trade_exec > 0 and ngq6_fills == 0:
        print("VERDICT=TRADE_EXEC_WITHOUT_FILL")
    elif ngq6_fills > 0:
        print("VERDICT=NGQ6_CLUSTER_ADVISORY_AND_FILL_OK")
    else:
        print("VERDICT=NGQ6_CLUSTER_ADVISORY_READY_WAIT_SIGNAL")

    print("NGQ6_PAPER_CLUSTER_BLOCK_ADVISORY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
