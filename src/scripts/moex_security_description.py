from __future__ import annotations

import argparse
import requests


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--secid", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    url = f"https://iss.moex.com/iss/securities/{args.secid}.json"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    desc = data.get("description") or {}
    columns = desc.get("columns") or []
    rows = desc.get("data") or []

    idx = {name: i for i, name in enumerate(columns)}

    values = {}

    for row in rows:
        name = str(row[idx["name"]])
        value = row[idx["value"]]
        values[name] = value

    for key in [
        "SECID",
        "SHORTNAME",
        "NAME",
        "TYPE",
        "GROUP",
        "PRIMARY_BOARDID",
        "MARKETCODE",
        "ENGINE",
    ]:
        print(f"MOEX_DESCRIPTION {key}={values.get(key)}", flush=True)

    boards = data.get("boards") or {}
    bcols = boards.get("columns") or []
    brows = boards.get("data") or []

    if bcols and brows:
        bidx = {name: i for i, name in enumerate(bcols)}

        for row in brows[:20]:
            boardid = row[bidx.get("boardid", 0)]
            engine = row[bidx.get("engine_id", bidx.get("engine", 0))]
            market = row[bidx.get("market_id", bidx.get("market", 0))]
            title = row[bidx.get("title", 0)]

            print(
                "MOEX_BOARD "
                f"board={boardid} "
                f"engine={engine} "
                f"market={market} "
                f"title={title}",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
