#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter


PATTERN = re.compile(
    r"PIPE_GUARD_EXECUTION_GATE_SHADOW "
    r".*?symbol=(?P<symbol>\S+) "
    r".*?strategy=(?P<strategy>\S+) "
    r".*?timeframe=(?P<timeframe>\S+) "
    r".*?side=(?P<side>\S+) "
    r".*?session=(?P<session>\S+) "
    r".*?classification=(?P<classification>\S+) "
    r".*?reason=(?P<reason>\S+) "
    r".*?would_block=(?P<would_block>\S+) "
    r".*?actual_block=(?P<actual_block>\S+)"
)


def read_journal(unit: str, since: str) -> list[str]:
    cmd = [
        "journalctl",
        "-u",
        unit,
        "--since",
        since,
        "--no-pager",
    ]
    out = subprocess.check_output(cmd, text=True, errors="replace")
    return out.splitlines()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", default="finam-paper-pipeline.service")
    parser.add_argument("--since", default="24 hours ago")
    args = parser.parse_args()

    lines = read_journal(args.unit, args.since)

    rows = []
    for line in lines:
        m = PATTERN.search(line)
        if not m:
            continue
        rows.append(m.groupdict())

    by_symbol = Counter()
    by_strategy = Counter()
    by_key = Counter()
    by_reason = Counter()

    for r in rows:
        by_symbol[r["symbol"]] += 1
        by_strategy[r["strategy"]] += 1
        by_reason[r["reason"]] += 1
        by_key[
            (
                r["symbol"],
                r["strategy"],
                r["timeframe"],
                r["side"],
                r["session"],
                r["classification"],
                r["reason"],
            )
        ] += 1

    total = len(rows)
    would_block = sum(1 for r in rows if r["would_block"] == "1")
    actual_block = sum(1 for r in rows if r["actual_block"] == "1")

    print("=== GUARD SHADOW EFFECTIVENESS REPORT V1 ===")
    print(f"unit={args.unit}")
    print(f"since={args.since}")
    print()
    print(f"SHADOW_TOTAL rows={total} would_block={would_block} actual_block={actual_block}")

    print()
    print("BY_SYMBOL")
    for symbol, cnt in by_symbol.most_common():
        print(f"SYMBOL_ROW symbol={symbol} shadow_blocks={cnt}")

    print()
    print("BY_STRATEGY")
    for strategy, cnt in by_strategy.most_common():
        print(f"STRATEGY_ROW strategy={strategy} shadow_blocks={cnt}")

    print()
    print("BY_REASON")
    for reason, cnt in by_reason.most_common():
        print(f"REASON_ROW reason={reason} shadow_blocks={cnt}")

    print()
    print("BY_FULL_KEY")
    for key, cnt in by_key.most_common():
        symbol, strategy, timeframe, side, session, classification, reason = key
        print(
            f"KEY_ROW symbol={symbol} strategy={strategy} timeframe={timeframe} "
            f"side={side} session={session} classification={classification} "
            f"reason={reason} shadow_blocks={cnt}"
        )

    print()
    if total == 0:
        print("VERDICT=NO_SHADOW_EVENTS_YET")
    else:
        print("VERDICT=OK")


if __name__ == "__main__":
    main()
