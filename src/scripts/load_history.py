# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from finam_core.ingestion.history_loader import HistoryLoader


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 1

    written = HistoryLoader().load_csv(
        path=path,
        symbol=args.symbol,
        timeframe=args.timeframe,
        batch_size=args.batch_size,
    )

    print(f"OK: loaded {written} bars into market_data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
