from __future__ import annotations

import argparse
import subprocess
import sys

from finam_core.research.ng_contract_universe import load_ng_contracts


def run(cmd: list[str]) -> None:
    print("RUN", " ".join(cmd), flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"NG_EXACT_SYMBOL_BACKFILL_FAILED code={result.returncode}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback-hours", type=int, default=1500)
    args = parser.parse_args()

    for symbol in load_ng_contracts():
        # Русский комментарий:
        # Пока backfill_finam_futures_market_bars работает по roots.
        # Поэтому этот скрипт фиксирует universe и даёт понятный контрольный вывод.
        print(
            f"NG_EXACT_SYMBOL_REQUEST symbol={symbol} timeframe={args.timeframe} "
            f"lookback_hours={args.lookback_hours}",
            flush=True,
        )

    print("NG_EXACT_SYMBOL_BACKFILL_NEEDS_CLIENT_SYMBOL_MODE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
