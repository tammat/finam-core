#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os

import psycopg

from finam_core.analytics.directional_edge_guard import DirectionalEdgeGuard


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--continuous-symbol", required=True)

    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)

    parser.add_argument("--side", required=True)
    parser.add_argument("--regime-direction", required=True)

    parser.add_argument("--guard-status", required=True)

    parser.add_argument("--trade-source", default="paper")

    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    guard = DirectionalEdgeGuard(mode="soft_advisory")

    decision = guard.decide(
        symbol=args.symbol,
        continuous_symbol=args.continuous_symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        side=args.side,
        regime_direction=args.regime_direction,
        guard_status=args.guard_status,
    )

    payload = {
        "symbol": args.symbol,
        "continuous_symbol": args.continuous_symbol,
        "strategy": args.strategy,
        "timeframe": args.timeframe,
        "side": args.side,
        "regime_direction": args.regime_direction,
        "guard_status": args.guard_status,
    }

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO directional_edge_telemetry (
                    symbol,
                    continuous_symbol,
                    strategy,
                    timeframe,
                    trade_source,
                    side,
                    regime_direction,
                    advisory_status,
                    advisory_reason,
                    guard_status,
                    guard_mode,
                    payload
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb
                )
                """,
                (
                    args.symbol,
                    args.continuous_symbol,
                    args.strategy,
                    args.timeframe,
                    args.trade_source,
                    args.side,
                    args.regime_direction,
                    decision.status,
                    decision.reason,
                    args.guard_status,
                    decision.mode,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    print(
        "DIRECTIONAL_EDGE_TELEMETRY_V1",
        f"symbol={args.symbol}",
        f"strategy={args.strategy}",
        f"timeframe={args.timeframe}",
        f"side={args.side}",
        f"regime_direction={args.regime_direction}",
        f"status={decision.status}",
        f"reason={decision.reason}",
        f"guard_mode={decision.mode}",
        flush=True,
    )


if __name__ == "__main__":
    main()
