from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from finam_core.ingestion.bars_client import FinamBarsClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--lookback-minutes", type=int, default=30)
    args = parser.parse_args()

    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=args.lookback_minutes)

    client = FinamBarsClient()
    ok = 0

    for raw in args.symbols.split(","):
        symbol = raw.strip()
        if not symbol:
            continue

        try:
            resp = client.get_bars(
                symbol=symbol,
                timeframe=args.timeframe,
                start=start,
                end=end,
            )
            bars = list(getattr(resp, "bars", []) or [])
            print(f"SYMBOL_PROBE_OK symbol={symbol} bars={len(bars)}")
            ok += 1
        except Exception as exc:
            msg = str(exc).replace("\n", " ")[:220]
            print(f"SYMBOL_PROBE_FAIL symbol={symbol} error={msg}")

    print(f"SYMBOL_PROBE_DONE ok={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
