from __future__ import annotations

import argparse
import subprocess
import sys

from finam_core.research.ng_contract_universe import load_ng_contracts


def run(cmd: list[str]) -> None:
    print("RUN", " ".join(cmd), flush=True)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--timeframe",
        default="M5",
    )

    parser.add_argument(
        "--trade-source",
        default="paper",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=180,
    )

    args = parser.parse_args()

    contracts = load_ng_contracts()

    for symbol in contracts:
        print(
            f"NG_UNIVERSE_REPLAY_START symbol={symbol}",
            flush=True,
        )

        run([
            sys.executable,
            "src/scripts/replay_ng_conservative_breakout.py",
            "--symbol", symbol,
            "--timeframe", args.timeframe,
            "--trade-source", args.trade_source,
            "--days", str(args.days),
        ])

        run([
            sys.executable,
            "src/scripts/build_trade_statistics_v2.py",
            "--symbol", symbol,
        ])

        run([
            sys.executable,
            "src/scripts/replay_exit_alpha_grid.py",
            "--symbol", symbol,
            "--strategy", "NG_CONSERVATIVE_BREAKOUT",
            "--timeframe", args.timeframe,
            "--trade-source", args.trade_source,
        ])

        print(
            f"NG_UNIVERSE_REPLAY_DONE symbol={symbol}",
            flush=True,
        )

    print(
        f"NG_UNIVERSE_REPLAY_SUMMARY contracts={len(contracts)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
