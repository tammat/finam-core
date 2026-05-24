from __future__ import annotations

import argparse
import subprocess
import sys


DEFAULT_SYMBOLS = [
    "NGM6@RTSX",
    "NGN6@RTSX",
    "NGQ6@RTSX",
    "NGU6@RTSX",
    "NGZ6@RTSX",
]


def run(cmd: list[str]) -> None:
    print("RUN:", " ".join(cmd), flush=True)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
    )

    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--limit", type=int, default=50000)

    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]

    for symbol in symbols:
        print(f"=== NG REPLAY EXPANSION {symbol} ===", flush=True)

        run([
            sys.executable,
            "src/scripts/replay_ng_conservative_breakout.py",
            "--symbols", symbol,
            "--timeframe", args.timeframe,
            "--limit", str(args.limit),
        ])

        run([
            sys.executable,
            "src/scripts/build_trade_fill_quality_audit.py",
            "--migrate",
            "--save",
            "--symbol", symbol,
            "--trade-source", "paper",
        ])

        run([
            sys.executable,
            "src/scripts/build_closed_trade_reconstruction_v2.py",
            "--migrate",
            "--symbol", symbol,
            "--trade-source", "paper",
            "--limit", "200000",
        ])

        run([
            sys.executable,
            "src/scripts/build_trade_attribution_v2.py",
            "--migrate",
            "--save",
            "--symbol", symbol,
            "--limit", "200000",
        ])

        run([
            sys.executable,
            "src/scripts/build_strategy_statistics_v2.py",
            "--migrate",
            "--save",
            "--symbol", symbol,
        ])

        run([
            sys.executable,
            "src/scripts/run_exit_alpha_parameter_grid.py",
            "--symbol", symbol,
            "--strategy", "NG_CONSERVATIVE_BREAKOUT",
            "--timeframe", args.timeframe,
            "--trade-source", "paper",
            "--bar-timeframe", args.timeframe,
        ])

        run([
            sys.executable,
            "src/scripts/build_best_exit_alpha_policy.py",
            "--symbol", symbol,
            "--strategy", "NG_CONSERVATIVE_BREAKOUT",
            "--timeframe", args.timeframe,
            "--trade-source", "paper",
            "--min-evaluated", "20",
            "--min-pf", "1.3",
            "--min-expectancy", "0",
        ])

    run([
        sys.executable,
        "src/scripts/sync_best_exit_alpha_to_radar.py",
    ])

    print("NG_REPLAY_EXPANSION_OK", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
