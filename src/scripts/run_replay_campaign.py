from __future__ import annotations

import argparse
import subprocess
import sys
import uuid
from datetime import datetime, timezone


DEFAULT_SYMBOLS = [
    "BRM6@RTSX",
    "SBER@MISX",
    "GAZP@MISX",
    "PLZL@MISX",
    "USDRUBF@RTSX",
]

DEFAULT_TIMEFRAMES = [
    "M5",
    "M15",
]

DEFAULT_STRATEGIES = [
    "BR_CONSERVATIVE_BREAKOUT",
    "VOLATILITY_BREAKOUT_EQUITY",
    "USDRUB_REGIME",
]


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--timeframes", default=",".join(DEFAULT_TIMEFRAMES))
    parser.add_argument("--strategies", default=",".join(DEFAULT_STRATEGIES))
    parser.add_argument("--campaign-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-secs", type=float, default=5.0)

    return parser.parse_args()


def normalize_strategy(strategy: str) -> str:
    strategy_map = {
        "BR_CONSERVATIVE_BREAKOUT": "breakout_reactive",
        "VOLATILITY_BREAKOUT_EQUITY": "breakout_reactive",
        "USDRUB_REGIME": "strategy_stack",
    }

    return strategy_map.get(strategy, strategy)


def build_replay_command(
    *,
    symbol: str,
    timeframe: str,
    strategy: str,
    campaign_id: str,
    replay_id: str,
    run_secs: float,
) -> list[str]:
    del timeframe
    del campaign_id
    del replay_id

    return [
        sys.executable,
        "src/scripts/run_market_pipeline.py",
        "--symbol",
        symbol,
        "--strategy",
        normalize_strategy(strategy),
        "--feed",
        "sim",
        "--run-secs",
        str(run_secs),
        "--risk-soft",
        "--exit-on-fill",
    ]


def main() -> int:
    args = parse_args()

    symbols = parse_csv(args.symbols)
    timeframes = parse_csv(args.timeframes)
    strategies = parse_csv(args.strategies)

    campaign_id = args.campaign_id or (
        "campaign-"
        + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:8]
    )

    total = 0
    failed = 0

    print(
        f"REPLAY_CAMPAIGN_START campaign_id={campaign_id} "
        f"symbols={len(symbols)} timeframes={len(timeframes)} strategies={len(strategies)} "
        f"dry_run={args.dry_run}",
        flush=True,
    )

    for symbol in symbols:
        for timeframe in timeframes:
            for strategy in strategies:
                replay_id = f"{campaign_id}:{symbol}:{timeframe}:{strategy}"
                cmd = build_replay_command(
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy=strategy,
                    campaign_id=campaign_id,
                    replay_id=replay_id,
                    run_secs=args.run_secs,
                )

                total += 1

                print(
                    "REPLAY_CAMPAIGN_RUN "
                    f"campaign_id={campaign_id} "
                    f"replay_id={replay_id} "
                    f"cmd={' '.join(cmd)}",
                    flush=True,
                )

                if args.dry_run:
                    continue

                result = subprocess.run(cmd)

                if result.returncode != 0:
                    failed += 1
                    print(
                        "REPLAY_CAMPAIGN_RUN_FAILED "
                        f"replay_id={replay_id} code={result.returncode}",
                        flush=True,
                    )

    print(
        f"REPLAY_CAMPAIGN_DONE campaign_id={campaign_id} total={total} failed={failed}",
        flush=True,
    )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
