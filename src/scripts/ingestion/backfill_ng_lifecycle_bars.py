from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("RUN", " ".join(cmd), flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"NG_LIFECYCLE_BACKFILL_FAILED code={result.returncode}", flush=True)


def main() -> int:
    # Русский комментарий:
    # Finam API по фьючерсам не всегда принимает слишком длинный диапазон.
    # Поэтому идём несколькими окнами: от длинного к короткому.
    windows = [4500, 3000, 1500, 750]

    for lookback_hours in windows:
        print(
            f"NG_LIFECYCLE_BACKFILL_WINDOW lookback_hours={lookback_hours}",
            flush=True,
        )

        run([
            sys.executable,
            "src/scripts/ingestion/backfill_finam_futures_market_bars.py",
            "--roots", "NG",
            "--timeframe", "M5",
            "--max-contracts", "7",
            "--lookback-hours", str(lookback_hours),
        ])

    print("NG_LIFECYCLE_BACKFILL_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
