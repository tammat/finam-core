from __future__ import annotations

import argparse
import requests


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=20)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    url = "https://iss.moex.com/iss/securities.json"
    params = {
        "q": args.query,
        "is_trading": 1,
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()
    block = data.get("securities") or {}
    columns = block.get("columns") or []
    rows = block.get("data") or []

    idx = {name: i for i, name in enumerate(columns)}

    printed = 0

    for row in rows:
        secid = str(row[idx.get("secid", 0)])
        name = str(row[idx.get("name", 0)])
        engine = str(row[idx.get("engine", 0)])
        market = str(row[idx.get("market", 0)])
        boardid = str(row[idx.get("boardid", 0)])

        print(
            "MOEX_SECURITY "
            f"secid={secid} "
            f"engine={engine} "
            f"market={market} "
            f"board={boardid} "
            f"name={name}",
            flush=True,
        )

        printed += 1

        if printed >= args.limit:
            break

    if printed == 0:
        print(f"MOEX_SECURITY_EMPTY query={args.query}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
