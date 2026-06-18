#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path


# Русский комментарий:
# SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1 — read-only план по сигналам.
# Скрипт использует результат SIGNAL_CLASS_EDGE_SCORECARD_V1_1 и классифицирует
# signal pairs в research candidates / quarantine / legacy / require more data.


def main() -> int:
    print("=== SIGNAL CLASS STRATEGY CANDIDATE PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print()

    cmd = [
        "python3",
        "src/scripts/research/build_signal_class_edge_scorecard_v1_1.py",
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    proc = subprocess.run(
        cmd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print("VERDICT=SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_FAILED_SCORECARD")
        return proc.returncode

    rows = []
    for line in proc.stdout.splitlines():
        if not line.startswith("SIGNAL_CLASS_EDGE_V1_1_ROW "):
            continue

        parts = line.split()[1:]
        row = {}
        for part in parts:
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            row[k] = v
        rows.append(row)

    print("SIGNAL_CLASS_STRATEGY_CANDIDATE_ROWS")

    promote = 0
    research_only = 0
    quarantine = 0
    more_data = 0
    legacy = 0

    for row in rows:
        entry = row.get("entry_signal_class", "UNKNOWN")
        exit_ = row.get("exit_signal_class", "UNKNOWN")
        strategy = row.get("strategy", "UNKNOWN")
        timeframe = row.get("timeframe", "UNKNOWN")
        family = row.get("family", "UNKNOWN")
        symbol = row.get("symbol", "UNKNOWN")
        closed_pairs = int(float(row.get("closed_pairs", "0")))
        net_pnl = float(row.get("net_pnl", "0"))
        net_pnl_per_pair = float(row.get("net_pnl_per_pair", "0"))
        edge_status = row.get("edge_status", "UNKNOWN")
        commission_drag_raw = row.get("commission_drag", "None")
        commission_drag = None if commission_drag_raw == "None" else float(commission_drag_raw)

        action = "REQUIRE_MORE_DATA"
        reason = "insufficient_decision_evidence"

        if entry == "UNCLASSIFIED_SIGNAL" or exit_ == "UNCLASSIFIED_SIGNAL" or strategy == "UNKNOWN":
            action = "LEGACY_DIRTY_DATA"
            reason = "unclassified_or_unknown_strategy"
            legacy += 1

        elif edge_status == "EDGE_NEGATIVE":
            action = "QUARANTINE_SIGNAL_CLASS"
            reason = "negative_closed_pair_edge"
            quarantine += 1

        elif edge_status == "EDGE_FLAT_OR_WEAK":
            action = "KEEP_RESEARCH_ONLY"
            reason = "flat_or_weak_edge"
            research_only += 1

        elif edge_status == "EDGE_POSITIVE":
            if closed_pairs >= 50 and net_pnl > 0 and net_pnl_per_pair > 0:
                if commission_drag is not None and commission_drag > 0.5:
                    action = "KEEP_RESEARCH_ONLY"
                    reason = "positive_but_commission_drag_high"
                    research_only += 1
                elif strategy in {"HISTORICAL_BREAKOUT_V1"}:
                    action = "KEEP_RESEARCH_ONLY"
                    reason = "historical_only_requires_live_confirmation"
                    research_only += 1
                elif "shadow" in strategy.lower():
                    action = "PROMOTE_TO_RESEARCH_CANDIDATE"
                    reason = "positive_shadow_edge_requires_paper_confirmation"
                    promote += 1
                elif family in {"ENERGY_GAS", "ENERGY_OIL", "FX_USDRUB"} and net_pnl_per_pair < 0.01:
                    # SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_1_STRICT_EDGE_FILTER
                    # Русский комментарий:
                    # Микро-edge по фьючерсам и валюте не продвигаем в research candidate.
                    # Его почти наверняка съедят комиссия, спред и проскальзывание.
                    action = "KEEP_RESEARCH_ONLY"
                    reason = "positive_but_micro_edge_below_execution_threshold"
                    research_only += 1
                else:
                    action = "PROMOTE_TO_RESEARCH_CANDIDATE"
                    reason = "positive_closed_pair_edge"
                    promote += 1
            else:
                action = "REQUIRE_MORE_DATA"
                reason = "positive_but_sample_too_small"
                more_data += 1

        else:
            more_data += 1

        print(
            "SIGNAL_CLASS_STRATEGY_CANDIDATE_ROW "
            f"entry_signal_class={entry} "
            f"exit_signal_class={exit_} "
            f"family={family} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"symbol={symbol} "
            f"closed_pairs={closed_pairs} "
            f"net_pnl={net_pnl:.6f} "
            f"net_pnl_per_pair={net_pnl_per_pair:.6f} "
            f"edge_status={edge_status} "
            f"action={action} "
            f"reason={reason}"
        )

    print()
    print("SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_SUMMARY")
    print(f"rows_total={len(rows)}")
    print(f"promote_to_research_candidate={promote}")
    print(f"keep_research_only={research_only}")
    print(f"quarantine_signal_class={quarantine}")
    print(f"require_more_data={more_data}")
    print(f"legacy_dirty_data={legacy}")

    print("VERDICT=SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_READY")
    print("SIGNAL_CLASS_STRATEGY_CANDIDATE_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
