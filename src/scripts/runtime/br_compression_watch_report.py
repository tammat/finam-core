from __future__ import annotations

import argparse
import re
import subprocess
from statistics import mean


PATTERN = re.compile(
    r"PIPE_BR_COMPRESSION_WATCH.*?"
    r"atr_pct=(?P<atr_pct>[0-9.]+).*?"
    r"threshold=(?P<threshold>[0-9.]+).*?"
    r"compression_ratio=(?P<compression_ratio>[0-9.]+).*?"
    r"reason=(?P<reason>[a-zA-Z0-9_]+).*?"
    r"mode=(?P<mode>[a-zA-Z0-9_]+).*?"
    r"price=(?P<price>[0-9.]+)"
)


def run_journalctl(since: str, unit: str) -> str:
    cmd = ["journalctl", "-u", unit, "--since", since, "--no-pager", "-l"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout or ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="today")
    parser.add_argument("--unit", default="finam-core")
    args = parser.parse_args()

    text = run_journalctl(args.since, args.unit)

    rows = []
    for line in text.splitlines():
        match = PATTERN.search(line)
        if not match:
            continue

        rows.append({
            "atr_pct": float(match.group("atr_pct")),
            "threshold": float(match.group("threshold")),
            "compression_ratio": float(match.group("compression_ratio")),
            "reason": match.group("reason"),
            "mode": match.group("mode"),
            "price": float(match.group("price")),
        })

    print(f"BR_COMPRESSION_WATCH_REPORT since={args.since} rows={len(rows)}")

    if not rows:
        return 0

    ratios = [r["compression_ratio"] for r in rows]
    atr_values = [r["atr_pct"] for r in rows]
    prices = [r["price"] for r in rows]

    print(
        "BR_COMPRESSION_WATCH_SUMMARY",
        f"avg_ratio={mean(ratios):.4f}",
        f"min_ratio={min(ratios):.4f}",
        f"max_ratio={max(ratios):.4f}",
        f"avg_atr_pct={mean(atr_values):.6f}",
        f"min_price={min(prices):.4f}",
        f"max_price={max(prices):.4f}",
    )

    by_mode: dict[str, int] = {}
    for row in rows:
        by_mode[row["mode"]] = by_mode.get(row["mode"], 0) + 1

    for mode, cnt in sorted(by_mode.items()):
        print("BR_COMPRESSION_WATCH_MODE", f"mode={mode}", f"count={cnt}")

    last = rows[-1]
    print(
        "BR_COMPRESSION_WATCH_LAST",
        f"compression_ratio={last['compression_ratio']:.4f}",
        f"atr_pct={last['atr_pct']:.6f}",
        f"threshold={last['threshold']:.6f}",
        f"mode={last['mode']}",
        f"reason={last['reason']}",
        f"price={last['price']:.4f}",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
