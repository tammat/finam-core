#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Row:
    underlying: str
    symbol: str
    strategy: str
    timeframe: str
    current_trades: int
    target_trades: int
    action: str
    first_entry: str
    last_exit: str


def parse_kv(line: str) -> dict[str, str]:
    return dict(re.findall(r"(\w+)=([^ ]+)", line))


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "src/scripts/analytics/build_accumulation_plan_v1.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    rows: list[Row] = []

    for line in proc.stdout.splitlines():
        if not line.startswith("ACCUMULATION_PLAN_ROW"):
            continue

        kv = parse_kv(line)
        rows.append(
            Row(
                underlying=kv.get("underlying", ""),
                symbol=kv.get("symbol", ""),
                strategy=kv.get("strategy", ""),
                timeframe=kv.get("timeframe", ""),
                current_trades=int(kv.get("current_trades", "0")),
                target_trades=int(kv.get("target_trades", "100")),
                action=kv.get("action", ""),
                first_entry=kv.get("first_entry", ""),
                last_exit=kv.get("last_exit", ""),
            )
        )

    ready = [r for r in rows if r.action == "READY_FOR_NEXT_VALIDATION"]
    work = [r for r in rows if r.action == "CONTINUE_PAPER_ACCUMULATION"]
    confirm = [r for r in rows if r.action == "PAPER_CONFIRMATION_REQUIRED"]

    print("=== СВОДКА НАКОПЛЕНИЯ СТАТИСТИКИ ===")
    print()

    print("ГОТОВЫ К СЛЕДУЮЩЕЙ ВАЛИДАЦИИ")
    if ready:
        for r in sorted(ready, key=lambda x: x.current_trades, reverse=True):
            print(f"{r.symbol:<14} {r.current_trades:>4}/{r.target_trades:<4} {r.strategy} {r.timeframe}")
    else:
        print("нет")

    print()
    print("НАКАПЛИВАЕМ ДАННЫЕ")
    if work:
        for r in sorted(work, key=lambda x: x.current_trades, reverse=True):
            pct = round((r.current_trades / r.target_trades) * 100, 1) if r.target_trades else 0
            print(f"{r.symbol:<14} {r.current_trades:>4}/{r.target_trades:<4} {pct:>5.1f}%  {r.strategy} {r.timeframe}")
    else:
        print("нет")

    print()
    print("ТРЕБУЮТ ПОДТВЕРЖДЕНИЯ PAPER")
    if confirm:
        for r in sorted(confirm, key=lambda x: x.current_trades, reverse=True):
            print(f"{r.symbol:<14} {r.current_trades:>4}/{r.target_trades:<4} {r.strategy} {r.timeframe}")
    else:
        print("нет")

    print()
    print("ФОКУС ПО СЫРЬЮ И ВАЛЮТЕ")
    focus = [r for r in rows if r.underlying in {"BRENT", "NATURAL_GAS", "USDRUB"}]
    for r in sorted(focus, key=lambda x: (x.underlying, -x.current_trades)):
        pct = round((r.current_trades / r.target_trades) * 100, 1) if r.target_trades else 0
        print(f"{r.underlying:<12} {r.symbol:<14} {r.current_trades:>4}/{r.target_trades:<4} {pct:>5.1f}%  {r.action}")

    print()
    print("ИТОГО")
    print(f"готовы={len(ready)}")
    print(f"накапливаем={len(work)}")
    print(f"требуют_подтверждения={len(confirm)}")
    print(f"всего_строк={len(rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
