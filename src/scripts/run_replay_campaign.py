from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone

from finam_core.replay.replay_campaign_telemetry import ReplayCampaignTelemetry
from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.replay.external_replay_adapter import ExternalReplayAdapter


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
    parser.add_argument("--data-source", choices=("sim", "moex"), default="sim")
    parser.add_argument("--date-from", default="")
    parser.add_argument("--date-to", default="")

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
    telemetry = None if args.dry_run else ReplayCampaignTelemetry(PostgresLogger())

    print(
        f"REPLAY_CAMPAIGN_START campaign_id={campaign_id} "
        f"symbols={len(symbols)} timeframes={len(timeframes)} strategies={len(strategies)} "
        f"data_source={args.data_source} dry_run={args.dry_run}",
        flush=True,
    )

    if args.data_source == "moex":
        if not args.date_from or not args.date_to:
            raise SystemExit("--date-from and --date-to are required for --data-source moex")

        adapter = ExternalReplayAdapter()

        for symbol in symbols:
            for timeframe in timeframes:
                events = adapter.load_events(
                    symbol=symbol,
                    timeframe=timeframe,
                    date_from=args.date_from,
                    date_to=args.date_to,
                )
                print(
                    "REPLAY_CAMPAIGN_MOEX_EVENTS "
                    f"campaign_id={campaign_id} symbol={symbol} timeframe={timeframe} "
                    f"date_from={args.date_from} date_to={args.date_to} events={len(events)}",
                    flush=True,
                )

        print(
            f"REPLAY_CAMPAIGN_DONE campaign_id={campaign_id} total=0 failed=0",
            flush=True,
        )
        return 0

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

                started_at = datetime.now(timezone.utc)
                env = os.environ.copy()
                env["SIMULATE_MARKET"] = "1"
                env["REPLAY_ACCUMULATION_MODE"] = "1"
                env["REPLAY_CAMPAIGN_ID"] = campaign_id
                env["REPLAY_ID"] = replay_id
                env["REPLAY_SYMBOL"] = symbol
                env["REPLAY_TIMEFRAME"] = timeframe
                env["REPLAY_STRATEGY"] = strategy
                env["PYTHONPATH"] = env.get("PYTHONPATH", "src")

                result = subprocess.run(cmd, env=env)
                finished_at = datetime.now(timezone.utc)
                duration_sec = (finished_at - started_at).total_seconds()

                status = "success" if result.returncode == 0 else "failed"

                if telemetry is not None:
                    telemetry.log_run(
                        campaign_id=campaign_id,
                        replay_id=replay_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy=strategy,
                        status=status,
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_sec=duration_sec,
                        return_code=result.returncode,
                        command=" ".join(cmd),
                        raw_json={
                            "normalized_strategy": normalize_strategy(strategy),
                        },
                    )

                if result.returncode != 0:
                    failed += 1
                    print(
                        "REPLAY_CAMPAIGN_RUN_FAILED "
                        f"replay_id={replay_id} code={result.returncode}",
                        flush=True,
                    )

    if not args.dry_run:
        build_cmd = [
            sys.executable,
            "src/scripts/build_replay_closed_trades.py",
            "--campaign-id",
            campaign_id,
        ]

        print(
            "REPLAY_CAMPAIGN_BUILD_CLOSED_TRADES "
            f"campaign_id={campaign_id} cmd={' '.join(build_cmd)}",
            flush=True,
        )

        build_result = subprocess.run(build_cmd)

        if build_result.returncode != 0:
            failed += 1
            print(
                "REPLAY_CAMPAIGN_BUILD_CLOSED_TRADES_FAILED "
                f"campaign_id={campaign_id} code={build_result.returncode}",
                flush=True,
            )

    print(
        f"REPLAY_CAMPAIGN_DONE campaign_id={campaign_id} total={total} failed={failed}",
        flush=True,
    )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
