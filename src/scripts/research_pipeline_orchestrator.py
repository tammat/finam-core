from __future__ import annotations

import argparse
import subprocess
import sys


def run_step(cmd: list[str], *, allow_fail: bool = False) -> int:
    print("RESEARCH_PIPELINE_CMD " + " ".join(cmd), flush=True)

    result = subprocess.run(cmd)

    if result.returncode != 0 and not allow_fail:
        print(
            "RESEARCH_PIPELINE_STEP_FAILED "
            f"rc={result.returncode} cmd={' '.join(cmd)}",
            flush=True,
        )
        return result.returncode

    return 0


def run_symbol(symbol: str, trade_source: str, limit: int) -> int:
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
            py, "src/scripts/build_runtime_strategy_selection.py",
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
        rc = run_step(step)
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

    failed = 0

    for symbol in symbols:
        rc = run_symbol(symbol, args.trade_source, args.limit)
        if rc != 0:
            failed += 1
            print(
                "RESEARCH_PIPELINE_SYMBOL_FAILED "
                f"symbol={symbol} rc={rc}",
                flush=True,
            )

    if args.sync_universe:
        rc = run_step([
            sys.executable,
            "src/scripts/sync_runtime_active_universe_from_strategy_selection.py",
        ])
        if rc != 0:
            failed += 1

    print(
        "RESEARCH_PIPELINE_SUMMARY "
        f"symbols={len(symbols)} failed={failed}",
        flush=True,
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
