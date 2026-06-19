#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg


ROOT = Path("/opt/finam-core")
SINCE_MSK = os.getenv("SINCE_MSK", "2026-06-19 10:24:35")
FUTURES_PREFIXES = os.getenv("FUTURES_PREFIXES", "BR,NG,GD")


def run_command(cmd: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode, output


def journal_count(pattern: str) -> int:
    code, output = run_command(
        [
            "journalctl",
            "-u",
            "finam-paper-pipeline.service",
            "--since",
            SINCE_MSK,
            "--no-pager",
        ]
    )
    if code != 0:
        return 0
    return sum(1 for line in output.splitlines() if pattern in line)


def source_has(path: str, pattern: str) -> int:
    full = ROOT / path
    if not full.exists():
        return 0
    return int(pattern in full.read_text(encoding="utf-8", errors="replace"))


def main() -> int:
    print("=== MULTI ASSET WATCH LAYER HEALTHCHECK V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"since_msk={SINCE_MSK}")
    print(f"futures_prefixes={FUTURES_PREFIXES}")

    py_files = [
        "src/finam_core/strategy/instrument_profile.py",
        "src/scripts/research/build_active_futures_contract_watchlist_expiry_plan_v1.py",
        "src/scripts/research/build_active_futures_contract_watchlist_selection_v1.py",
        "src/scripts/research/build_multi_asset_breakout_watch_v2.py",
        "src/scripts/research/build_equity_runtime_dispatch_churn_audit_v1.py",
    ]

    compile_failures = []
    for file_name in py_files:
        code, output = run_command(["python3", "-m", "py_compile", file_name])
        if code != 0:
            compile_failures.append((file_name, output.strip()))

    print()
    print("MULTI_ASSET_WATCH_SOURCE_ROWS")
    print(f"SOURCE_HAS_INSTRUMENT_PROFILE={source_has('src/finam_core/strategy/instrument_profile.py', 'InstrumentSignalProfile')}")
    print(f"SOURCE_HAS_BRENT_PROFILE={source_has('src/finam_core/strategy/instrument_profile.py', 'BRENT_FUTURES')}")
    print(f"SOURCE_HAS_GAS_PROFILE={source_has('src/finam_core/strategy/instrument_profile.py', 'GAS_FUTURES')}")
    print(f"SOURCE_HAS_GOLD_PROFILE={source_has('src/finam_core/strategy/instrument_profile.py', 'GOLD_FUTURES')}")
    print(f"SOURCE_HAS_EQUITY_PROFILE={source_has('src/finam_core/strategy/instrument_profile.py', 'EQUITY')}")
    print(f"SOURCE_HAS_EQUITY_HANDLER_CALL={source_has('src/finam_core/pipelines/paper_pipeline.py', '_process_equity_closed_bar_for_paper_signal(bar)')}")
    print(f"SOURCE_HAS_EQUITY_HANDLER_DEF={source_has('src/finam_core/pipelines/paper_pipeline.py', 'def _process_equity_closed_bar_for_paper_signal')}")
    print(f"SOURCE_HAS_EQUITY_ROUTE_LOG={source_has('src/finam_core/pipelines/paper_pipeline.py', 'PIPE_EQUITY_CLOSED_BAR_ROUTE')}")
    print(f"SOURCE_HAS_V2_WATCH={source_has('src/scripts/research/build_multi_asset_breakout_watch_v2.py', 'MULTI_ASSET_BREAKOUT_WATCH_V2')}")
    print(f"py_compile_failures={len(compile_failures)}")

    for file_name, error in compile_failures:
        print(
            "MULTI_ASSET_WATCH_PY_COMPILE_FAILURE "
            f"file={file_name} error={error[:400]}"
        )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    runtime_equity_rows = 0
    selected_futures_output = ""
    v2_output = ""
    expiry_output = ""

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select count(*)::int
                from runtime_active_universe
                where is_enabled = true
                  and symbol like %s
                """,
                ("%@MISX",),
            )
            runtime_equity_rows = int(cur.fetchone()[0] or 0)

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
            active_equities = cur.fetchall()

    print()
    print("MULTI_ASSET_WATCH_ACTIVE_EQUITY_ROWS")
    for symbol, strategy, timeframe, is_enabled, score, updated_at in active_equities:
        print(
            "MULTI_ASSET_WATCH_ACTIVE_EQUITY_ROW "
            f"symbol={symbol} strategy={strategy} timeframe={timeframe} "
            f"is_enabled={int(bool(is_enabled))} score={score} updated_at={updated_at}"
        )

    print()
    print("MULTI_ASSET_WATCH_JOURNAL_ROWS")
    equity_route_logs = journal_count("PIPE_EQUITY_CLOSED_BAR_ROUTE")
    equity_no_signal_logs = journal_count("PIPE_EQUITY_CLOSED_BAR_NO_SIGNAL")
    equity_signal_logs = journal_count("PIPE_EQUITY_CLOSED_BAR_SIGNAL")
    tracebacks = journal_count("Traceback")
    errors = journal_count("ERROR")

    print(f"journal_equity_route_logs={equity_route_logs}")
    print(f"journal_equity_no_signal_logs={equity_no_signal_logs}")
    print(f"journal_equity_signal_logs={equity_signal_logs}")
    print(f"journal_tracebacks={tracebacks}")
    print(f"journal_errors={errors}")

    code, expiry_output = run_command(
        ["python3", "src/scripts/research/build_active_futures_contract_watchlist_expiry_plan_v1.py"],
        env={"PYTHONPATH": "src", "FUTURES_PREFIXES": FUTURES_PREFIXES},
    )
    expiry_ok = int(code == 0 and "ACTIVE_FUTURES_CONTRACT_WATCHLIST_EXPIRY_PLAN_V1_OK" in expiry_output)

    code, selected_futures_output = run_command(
        ["python3", "src/scripts/research/build_active_futures_contract_watchlist_selection_v1.py"],
        env={"PYTHONPATH": "src", "FUTURES_PREFIXES": FUTURES_PREFIXES},
    )
    selection_ok = int(code == 0 and "ACTIVE_FUTURES_CONTRACT_WATCHLIST_SELECTION_V1_OK" in selected_futures_output)

    code, v2_output = run_command(
        ["python3", "src/scripts/research/build_multi_asset_breakout_watch_v2.py"],
        env={"PYTHONPATH": "src", "FUTURES_PREFIXES": FUTURES_PREFIXES},
    )
    v2_ok = int(code == 0 and "MULTI_ASSET_BREAKOUT_WATCH_V2_OK" in v2_output)

    def metric_from_output(output: str, key: str) -> str:
        for line in output.splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
        return "UNKNOWN"

    print()
    print("MULTI_ASSET_WATCH_COMPONENT_ROWS")
    print(f"expiry_plan_ok={expiry_ok}")
    print(f"expiry_watch_candidates={metric_from_output(expiry_output, 'watch_candidates')}")
    print(f"expiry_fresh_rows={metric_from_output(expiry_output, 'fresh_rows')}")
    print(f"expiry_expired_rows={metric_from_output(expiry_output, 'expired_rows')}")
    print(f"selection_ok={selection_ok}")
    print(f"selection_families_total={metric_from_output(selected_futures_output, 'families_total')}")
    print(f"selection_primary_total={metric_from_output(selected_futures_output, 'primary_total')}")
    print(f"selection_secondary_total={metric_from_output(selected_futures_output, 'secondary_total')}")
    print(f"selection_research_total={metric_from_output(selected_futures_output, 'research_total')}")
    print(f"v2_ok={v2_ok}")
    print(f"v2_universe_total={metric_from_output(v2_output, 'universe_total')}")
    print(f"v2_rows_total={metric_from_output(v2_output, 'rows_total')}")
    print(f"v2_equity_rows={metric_from_output(v2_output, 'equity_rows')}")
    print(f"v2_futures_rows={metric_from_output(v2_output, 'futures_rows')}")
    print(f"v2_breakout_ready={metric_from_output(v2_output, 'breakout_ready')}")
    print(f"v2_no_breakout={metric_from_output(v2_output, 'no_breakout')}")
    print(f"v2_atr_blocked={metric_from_output(v2_output, 'atr_blocked')}")
    print(f"v2_volume_blocked={metric_from_output(v2_output, 'volume_blocked')}")

    source_ok = (
        source_has('src/finam_core/strategy/instrument_profile.py', 'BRENT_FUTURES')
        and source_has('src/finam_core/strategy/instrument_profile.py', 'GAS_FUTURES')
        and source_has('src/finam_core/strategy/instrument_profile.py', 'GOLD_FUTURES')
        and source_has('src/finam_core/pipelines/paper_pipeline.py', 'PIPE_EQUITY_CLOSED_BAR_ROUTE')
        and source_has('src/scripts/research/build_multi_asset_breakout_watch_v2.py', 'MULTI_ASSET_BREAKOUT_WATCH_V2')
    )

    v2_ready = metric_from_output(v2_output, "breakout_ready")
    breakout_ready = int(v2_ready) if str(v2_ready).isdigit() else 0

    print()
    print("MULTI_ASSET_WATCH_LAYER_HEALTHCHECK_SUMMARY")
    print(f"source_ok={int(bool(source_ok))}")
    print(f"runtime_equity_rows={runtime_equity_rows}")
    print(f"expiry_plan_ok={expiry_ok}")
    print(f"selection_ok={selection_ok}")
    print(f"v2_ok={v2_ok}")
    print(f"breakout_ready={breakout_ready}")
    print(f"py_compile_failures={len(compile_failures)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not source_ok or compile_failures:
        print("VERDICT=MULTI_ASSET_WATCH_LAYER_SOURCE_OR_COMPILE_FAIL")
    elif expiry_ok and selection_ok and v2_ok and breakout_ready == 0:
        print("VERDICT=MULTI_ASSET_WATCH_LAYER_OK_NO_READY_SETUPS")
    elif expiry_ok and selection_ok and v2_ok and breakout_ready > 0:
        print("VERDICT=MULTI_ASSET_WATCH_LAYER_OK_HAS_READY_SETUPS")
    else:
        print("VERDICT=MULTI_ASSET_WATCH_LAYER_REVIEW_REQUIRED")

    print("MULTI_ASSET_WATCH_LAYER_HEALTHCHECK_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
