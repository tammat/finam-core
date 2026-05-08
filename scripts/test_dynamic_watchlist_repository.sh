#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.storage.dynamic_watchlist_repository import DynamicWatchlistRepository

repo = DynamicWatchlistRepository()

rows = [
    {
        "symbol": "YDEX@MISX",
        "name": "ЯНДЕКС",
        "direction": "GAINER",
        "score": 9.5,
        "relative_strength": 10.1,
        "portfolio_status": "NEW_CANDIDATE",
        "portfolio_action": "WATCH_FOR_ENTRY",
    },
    {
        "symbol": "SBER@MISX",
        "name": "Сбербанк",
        "direction": "LOSER",
        "score": 2.0,
        "relative_strength": -1.5,
        "portfolio_status": "ALREADY_HELD_LONG",
        "portfolio_action": "EXIT_WATCH",
    },
]

saved = repo.replace_watchlist(rows)

assert saved == 2

loaded = repo.load_watchlist()

assert len(loaded) >= 2

symbols = {x["symbol"] for x in loaded}

assert "YDEX@MISX" in symbols
assert "SBER@MISX" in symbols

print("DYNAMIC_WATCHLIST_REPOSITORY_OK")
PY
