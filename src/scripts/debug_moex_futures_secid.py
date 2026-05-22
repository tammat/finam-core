from __future__ import annotations

import argparse
import requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    q = args.query.upper()

    url = "https://iss.moex.com/iss/engines/futures/markets/forts/securities.json"

    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    securities = data.get("securities", {})
    columns = securities.get("columns", [])
    rows = securities.get("data", [])

    matches = []

    for row in rows:
        item = dict(zip(columns, row))

        haystack = " ".join(
            str(item.get(k, "") or "").upper()
            for k in ["SECID", "SHORTNAME", "SECNAME", "LATNAME", "ASSETCODE"]
        )

        if q in haystack:
            matches.append(item)

    print("MATCHES:", len(matches))

    for item in matches[:80]:
        print(
            item.get("SECID"),
            item.get("BOARDID"),
            item.get("SHORTNAME"),
            item.get("ASSETCODE"),
            item.get("SECNAME"),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
