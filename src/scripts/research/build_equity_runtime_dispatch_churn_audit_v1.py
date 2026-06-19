#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
from collections import Counter
from pathlib import Path

import psycopg


ROOT = Path("/opt/finam-core")
ACTIVE_SINCE_MSK = os.getenv("ACTIVE_SINCE_MSK", "2026-06-19 09:13:38")
ACTIVE_SINCE_UTC = os.getenv("ACTIVE_SINCE_UTC", "2026-06-19 06:13:38+00")


PATTERNS = {
    "runtime_created": "PIPE_RUNTIME_SYMBOL_STRATEGY_CREATED",
    "mtf_closed": "PIPE_MTF_BAR_CLOSED",
    "equity_route": "PIPE_EQUITY_CLOSED_BAR_ROUTE",
    "equity_no_signal": "PIPE_EQUITY_CLOSED_BAR_NO_SIGNAL",
    "equity_signal": "PIPE_EQUITY_CLOSED_BAR_SIGNAL",
    "traceback": "Traceback",
    "error": "ERROR",
}


def env_flag(name: str) -> str:
    return os.getenv(name, "0")


def run_journal() -> str:
    cmd = [
        "journalctl",
        "-u",
        "finam-paper-pipeline.service",
        "--since",
        ACTIVE_SINCE_MSK,
        "--no-pager",
    ]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return (result.stdout or "") + "\n" + (result.stderr or "")


def source_has(pattern: str) -> bool:
    path = ROOT / "src/finam_core/pipelines/paper_pipeline.py"
    text = path.read_text(encoding="utf-8", errors="replace")
    return pattern in text


def main() -> int:
    print("=== EQUITY RUNTIME DISPATCH CHURN AUDIT V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={env_flag('RUNTIME_ALLOW_TRADING')}")
    print(f"execution_enabled={env_flag('EXECUTION_ENABLED')}")
    print(f"real_trading_enabled={env_flag('REAL_TRADING_ENABLED')}")
    print("db_update=0")
    print(f"active_since_msk={ACTIVE_SINCE_MSK}")
    print(f"active_since_utc={ACTIVE_SINCE_UTC}")

    journal = run_journal()
    lines = [line for line in journal.splitlines() if line.strip()]

    counts = {name: sum(1 for line in lines if pattern in line) for name, pattern in PATTERNS.items()}

    created_symbols: Counter[str] = Counter()
    for line in lines:
        if PATTERNS["runtime_created"] not in line:
            continue
        match = re.search(r"symbol=([^ ]+)", line)
        if match:
            created_symbols[match.group(1)] += 1

    print()
    print("EQUITY_RUNTIME_DISPATCH_SOURCE_ROWS")
    print(f"SOURCE_HAS_EQUITY_HANDLER_CALL={int(source_has('_process_equity_closed_bar_for_paper_signal(bar)'))}")
    print(f"SOURCE_HAS_EQUITY_HANDLER_DEF={int(source_has('def _process_equity_closed_bar_for_paper_signal'))}")
    print(f"SOURCE_HAS_EQUITY_ROUTE_LOG={int(source_has('PIPE_EQUITY_CLOSED_BAR_ROUTE'))}")
    print(f"SOURCE_HAS_EQUITY_TRACE_ONLY={int(source_has('execution=disabled_trace_only'))}")

    print()
    print("EQUITY_RUNTIME_DISPATCH_JOURNAL_ROWS")
    for name, value in counts.items():
        print(f"EQUITY_RUNTIME_DISPATCH_JOURNAL_ROW event={name} rows={value}")

    print()
    print("EQUITY_RUNTIME_STRATEGY_CREATED_ROWS")
    for symbol, count in created_symbols.most_common():
        print(f"EQUITY_RUNTIME_STRATEGY_CREATED_ROW symbol={symbol} rows={count}")

    database_url = os.getenv("DATABASE_URL")
    runtime_rows = []
    bar_rows = []
    guard_rows = []
    signal_rows = []

    if database_url:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select symbol, strategy, timeframe, is_enabled, score, updated_at
                    from runtime_active_universe
                    where is_enabled = true
                      and symbol like %s
                    order by symbol
                    """
                ,
                    ("%@MISX",),
                )
                runtime_rows = cur.fetchall()

                cur.execute(
                    """
                    select symbol, count(*)::int, min(ts), max(ts)
                    from market_bars
                    where symbol like %s
                      and timeframe = 'M5'
                      and ts >= %s::timestamptz
                    group by symbol
                    order by symbol
                    """,
                    ("%@MISX", ACTIVE_SINCE_UTC),
                )
                bar_rows = cur.fetchall()

                cur.execute(
                    """
                    select symbol, strategy, block_type, block_reason, count(*)::int, min(ts), max(ts)
                    from runtime_guard_pre_signal_block_audit_v1
                    where symbol like %s
                      and ts >= %s::timestamptz
                    group by symbol, strategy, block_type, block_reason
                    order by max(ts) desc nulls last
                    """,
                    ("%@MISX", ACTIVE_SINCE_UTC),
                )
                guard_rows = cur.fetchall()

                cur.execute(
                    """
                    select symbol, strategy, status, count(*)::int, min(created_at), max(created_at)
                    from signals
                    where symbol like %s
                      and created_at >= %s::timestamptz
                    group by symbol, strategy, status
                    order by max(created_at) desc nulls last
                    """,
                    ("%@MISX", ACTIVE_SINCE_UTC),
                )
                signal_rows = cur.fetchall()

    print()
    print("EQUITY_RUNTIME_ACTIVE_EQUITY_ROWS")
    for row in runtime_rows:
        print(
            "EQUITY_RUNTIME_ACTIVE_EQUITY_ROW "
            f"symbol={row[0]} strategy={row[1]} timeframe={row[2]} "
            f"is_enabled={int(bool(row[3]))} score={row[4]} updated_at={row[5]}"
        )

    print()
    print("EQUITY_RUNTIME_FRESH_BAR_ROWS")
    for row in bar_rows:
        print(
            "EQUITY_RUNTIME_FRESH_BAR_ROW "
            f"symbol={row[0]} bars_after_restart={row[1]} first_ts={row[2]} last_ts={row[3]}"
        )

    print()
    print("EQUITY_RUNTIME_FRESH_GUARD_ROWS")
    for row in guard_rows:
        print(
            "EQUITY_RUNTIME_FRESH_GUARD_ROW "
            f"symbol={row[0]} strategy={row[1]} block_type={row[2]} reason={row[3]} "
            f"rows={row[4]} first_ts={row[5]} last_ts={row[6]}"
        )

    print()
    print("EQUITY_RUNTIME_FRESH_SIGNAL_ROWS")
    for row in signal_rows:
        print(
            "EQUITY_RUNTIME_FRESH_SIGNAL_ROW "
            f"symbol={row[0]} strategy={row[1]} status={row[2]} rows={row[3]} "
            f"first_ts={row[4]} last_ts={row[5]}"
        )

    source_ok = (
        source_has("_process_equity_closed_bar_for_paper_signal(bar)")
        and source_has("def _process_equity_closed_bar_for_paper_signal")
        and source_has("PIPE_EQUITY_CLOSED_BAR_ROUTE")
    )
    bars_after_restart_total = sum(int(row[1] or 0) for row in bar_rows)
    guard_after_restart_total = sum(int(row[4] or 0) for row in guard_rows)
    signal_after_restart_total = sum(int(row[3] or 0) for row in signal_rows)
    runtime_created_total = sum(created_symbols.values())

    print()
    print("EQUITY_RUNTIME_DISPATCH_CHURN_AUDIT_SUMMARY")
    print(f"source_ok={int(source_ok)}")
    print(f"runtime_created_total={runtime_created_total}")
    print(f"runtime_created_unique_symbols={len(created_symbols)}")
    print(f"mtf_closed_logs={counts['mtf_closed']}")
    print(f"equity_route_logs={counts['equity_route']}")
    print(f"equity_no_signal_logs={counts['equity_no_signal']}")
    print(f"equity_signal_logs={counts['equity_signal']}")
    print(f"bars_after_restart_total={bars_after_restart_total}")
    print(f"guard_after_restart_total={guard_after_restart_total}")
    print(f"signal_after_restart_total={signal_after_restart_total}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={env_flag('REAL_TRADING_ENABLED')}")
    print(f"execution_enabled={env_flag('EXECUTION_ENABLED')}")

    if not source_ok:
        print("VERDICT=EQUITY_DISPATCH_PATCH_NOT_PRESENT_IN_SOURCE")
    elif bars_after_restart_total > 0 and counts["mtf_closed"] == 0:
        print("VERDICT=EQUITY_BARS_WRITTEN_BUT_MTF_CALLBACK_NOT_LOGGED")
    elif bars_after_restart_total > 0 and counts["mtf_closed"] > 0 and counts["equity_route"] == 0:
        print("VERDICT=MTF_CALLBACK_LOGGED_BUT_EQUITY_ROUTE_NOT_LOGGED")
    elif runtime_created_total >= 10 and counts["equity_route"] == 0:
        print("VERDICT=RUNTIME_STRATEGY_CHURN_WITHOUT_EQUITY_ROUTE")
    elif counts["equity_route"] > 0 and counts["equity_signal"] == 0:
        print("VERDICT=EQUITY_ROUTE_REACHED_NO_SIGNAL")
    elif counts["equity_signal"] > 0:
        print("VERDICT=EQUITY_SIGNAL_REACHED_TRACE_ONLY")
    else:
        print("VERDICT=EQUITY_RUNTIME_DISPATCH_CHURN_REVIEW_REQUIRED")

    print("EQUITY_RUNTIME_DISPATCH_CHURN_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
