from __future__ import annotations

import argparse
import subprocess
import sys

from finam_core.analytics.research_pipeline_run_log import ResearchPipelineRunLog


def run_step(
    cmd: list[str],
    *,
    allow_fail: bool = False,
    run_log: ResearchPipelineRunLog | None = None,
    run_id: int | None = None,
    symbol: str = "",
    step_name: str = "",
) -> int:
    command = " ".join(cmd)
    print("RESEARCH_PIPELINE_CMD " + command, flush=True)

    step_id = None
    started = None

    if run_log is not None and run_id is not None:
        step_id = run_log.start_step(
            run_id=run_id,
            symbol=symbol,
            step_name=step_name or cmd[1] if len(cmd) > 1 else command,
            command=command,
        )
        started = run_log.monotonic()

    result = subprocess.run(cmd)

    if run_log is not None and step_id is not None and started is not None:
        run_log.finish_step(
            step_id=step_id,
            return_code=result.returncode,
            duration_sec=round(run_log.monotonic() - started, 6),
            error_message="" if result.returncode == 0 else "step_failed",
        )

    if result.returncode != 0 and not allow_fail:
        print(
            "RESEARCH_PIPELINE_STEP_FAILED "
            f"rc={result.returncode} cmd={command}",
            flush=True,
        )
        return result.returncode

    return 0


def run_symbol(symbol: str, trade_source: str, limit: int, *, run_log: ResearchPipelineRunLog | None = None, run_id: int | None = None) -> int:
    print(
        "RESEARCH_PIPELINE_SYMBOL_START "
        f"symbol={symbol} source={trade_source}",
        flush=True,
    )

    py = sys.executable

    steps = [
        [
            py, "src/scripts/build_trade_fill_quality_audit.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--trade-source", trade_source,
        ],
        [
            py, "src/scripts/build_closed_trade_reconstruction_v2.py",
            "--migrate",
            "--symbol", symbol,
            "--trade-source", trade_source,
            "--limit", str(limit),
        ],
        [
            py, "src/scripts/build_trade_attribution_v2.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--limit", str(limit),
        ],
        [
            py, "src/scripts/build_trade_risk_context.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--limit", str(limit),
        ],
        [
            py, "src/scripts/build_trade_context_snapshots.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--limit", str(limit),
        ],
        [
            py, "src/scripts/build_strategy_statistics_v2.py",
            "--migrate", "--save",
            "--symbol", symbol,
        ],
        [
            py, "src/scripts/build_strategy_ranking_v2.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--limit", "50",
        ],
        [
            py, "src/scripts/build_strategy_promotion_feed.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--limit", "50",
        ],
        [
            py, "src/scripts/runtime/build_runtime_strategy_selection.py",
            "--symbol", symbol,
            "--limit", "50",
        ],
        [
            py, "src/scripts/build_strategy_lifecycle_state.py",
            "--migrate", "--save",
            "--symbol", symbol,
            "--limit", "50",
        ],
        [
            py, "src/scripts/build_strategy_promotion_engine_v1.py",
            "--migrate", "--save", "--apply-lifecycle",
            "--symbol", symbol,
            "--limit", "50",
        ],
    ]

    for step in steps:
        step_name = step[1].split("/")[-1] if len(step) > 1 else "unknown"
        rc = run_step(
            step,
            run_log=run_log,
            run_id=run_id,
            symbol=symbol,
            step_name=step_name,
        )
        if rc != 0:
            return rc

    print(
        "RESEARCH_PIPELINE_SYMBOL_OK "
        f"symbol={symbol} source={trade_source}",
        flush=True,
    )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--sync-universe", action="store_true")
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]

    print(
        "RESEARCH_PIPELINE_START "
        f"symbols={len(symbols)} source={args.trade_source}",
        flush=True,
    )

    cleanup_rc = run_step([
        sys.executable,
        "src/scripts/cleanup_invalid_strategy_rows.py",
    ])
    if cleanup_rc != 0:
        return cleanup_rc

    run_log = ResearchPipelineRunLog()
    run_log.migrate()
    run_id = run_log.start_run(
        trade_source=args.trade_source,
        symbols_total=len(symbols),
    )

    failed = 0
    ok = 0

    for symbol in symbols:
        rc = run_symbol(
            symbol,
            args.trade_source,
            args.limit,
            run_log=run_log,
            run_id=run_id,
        )
        if rc != 0:
            failed += 1
            print(
                "RESEARCH_PIPELINE_SYMBOL_FAILED "
                f"symbol={symbol} rc={rc}",
                flush=True,
            )
        else:
            ok += 1

    if args.sync_universe:
        rc = run_step(
            [
                sys.executable,
                "src/scripts/sync_runtime_active_universe_from_strategy_selection.py",
            ],
            run_log=run_log,
            run_id=run_id,
            symbol="*",
            step_name="sync_runtime_active_universe",
        )
        if rc != 0:
            failed += 1

    final_status = "OK" if failed == 0 else "FAILED"
    run_log.finish_run(
        run_id=run_id,
        symbols_ok=ok,
        symbols_failed=failed,
        status=final_status,
        error_message="" if failed == 0 else "one_or_more_symbols_failed",
    )

    print(
        "RESEARCH_PIPELINE_SUMMARY "
        f"run_id={run_id} symbols={len(symbols)} ok={ok} failed={failed}",
        flush=True,
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
