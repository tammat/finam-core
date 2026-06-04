#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SYMBOL = os.getenv("SYMBOL", "NGN6@RTSX")
ROOT = Path(__file__).resolve().parents[3]
STATS_SCRIPT = ROOT / "src/scripts/analytics/build_ng_runtime_governance_statistics_v1.py"


def run_stats() -> str:
    env = dict(os.environ)
    env["SYMBOL"] = SYMBOL

    result = subprocess.run(
        [sys.executable, str(STATS_SCRIPT)],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout


def parse_value(text: str, key: str, block: str | None = None) -> str | None:
    lines = text.splitlines()
    active = block is None

    for line in lines:
        stripped = line.strip()

        if block and stripped == block:
            active = True
            continue

        if active and stripped.startswith("PERFORMANCE_") and stripped != block:
            if block:
                active = False

        if active and stripped.startswith(f"{key}="):
            return stripped.split("=", 1)[1]

    return None


def as_float(value: str | None) -> float | None:
    if value in (None, "", "None"):
        return None
    if value == "inf":
        return float("inf")
    try:
        return float(value)
    except Exception:
        return None


def as_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def main() -> int:
    stats = run_stats()

    closed_all = as_int(parse_value(stats, "closed_trades", "PERFORMANCE_ALL"))
    closed_qty1 = as_int(parse_value(stats, "closed_trades", "PERFORMANCE_QTY_EQ_1"))

    expectancy_all = as_float(parse_value(stats, "expectancy_points", "PERFORMANCE_ALL"))
    expectancy_qty1 = as_float(parse_value(stats, "expectancy_points", "PERFORMANCE_QTY_EQ_1"))

    pf_all = as_float(parse_value(stats, "profit_factor", "PERFORMANCE_ALL"))
    pf_qty1 = as_float(parse_value(stats, "profit_factor", "PERFORMANCE_QTY_EQ_1"))

    winrate_all = as_float(parse_value(stats, "winrate", "PERFORMANCE_ALL"))
    winrate_qty1 = as_float(parse_value(stats, "winrate", "PERFORMANCE_QTY_EQ_1"))

    if closed_qty1 < 30:
        edge_status = "WEAK_SAMPLE"
        verdict = "RESEARCH_ONLY"
        reason = "insufficient_qty1_closed_trades"
    elif expectancy_qty1 is None or expectancy_qty1 <= 0:
        edge_status = "WEAK"
        verdict = "REJECT"
        reason = "non_positive_expectancy_qty1"
    elif pf_qty1 is None or pf_qty1 < 1.10:
        edge_status = "WEAK"
        verdict = "REJECT"
        reason = "profit_factor_qty1_below_1_10"
    elif pf_qty1 >= 1.30 and expectancy_qty1 > 0:
        edge_status = "STRONG"
        verdict = "PROMOTE_RUNTIME"
        reason = "positive_expectancy_and_pf_qty1_above_1_30"
    else:
        edge_status = "NEUTRAL"
        verdict = "RESEARCH_ONLY"
        reason = "edge_positive_but_not_strong"

    print("=== NG EDGE SCORECARD V1 ===")
    print(f"symbol={SYMBOL}")
    print()

    print("EDGE QUALITY")
    print(f"closed_trades_all={closed_all}")
    print(f"closed_trades_qty1={closed_qty1}")
    print(f"expectancy_all={expectancy_all}")
    print(f"expectancy_qty1={expectancy_qty1}")
    print(f"profit_factor_all={pf_all}")
    print(f"profit_factor_qty1={pf_qty1}")
    print(f"winrate_all={winrate_all}")
    print(f"winrate_qty1={winrate_qty1}")
    print()

    print("EDGE STATUS")
    print(f"status={edge_status}")
    print()

    print("FINAL VERDICT")
    print(f"verdict={verdict}")
    print(f"reason={reason}")
    print()

    print("SOURCE_REPORT")
    print("script=build_ng_runtime_governance_statistics_v1.py")
    print("note=scorecard_uses_qty1_metrics_as_primary_runtime_gate")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
