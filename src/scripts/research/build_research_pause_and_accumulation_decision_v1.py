#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess


# Русский комментарий:
# RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_V1 — read-only финальный decision gate.
# Он не пишет в БД, не меняет runtime_active_universe, не включает execution.
# Цель — зафиксировать, что текущий research-цикл не дал новых кандидатов,
# поэтому система переходит в режим накопления данных без расширения стратегий.


def run_script(path: str) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    proc = subprocess.run(
        ["python3", path],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def parse_kv(output: str) -> dict[str, str]:
    result: dict[str, str] = {}

    for line in output.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key:
            result[key] = value

    return result


def find_line(output: str, prefix: str) -> str:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line
    return ""


def as_int(value: str | None) -> int:
    if value is None or value == "":
        return 0
    return int(float(value))


def check_research_candidate_empty() -> dict[str, str]:
    path = "src/scripts/research/build_research_candidate_empty_decision_v1.py"
    rc, output = run_script(path)
    kv = parse_kv(output)

    decision = kv.get("decision", "UNKNOWN")
    verdict = kv.get("VERDICT", "UNKNOWN")
    checks_failed = as_int(kv.get("checks_failed"))
    new_candidates = as_int(kv.get("new_strategy_candidates"))
    runtime_changes = as_int(kv.get("runtime_changes_required"))
    execution_changes = as_int(kv.get("execution_changes_required"))

    status = (
        "PASS"
        if rc == 0
        and checks_failed == 0
        and new_candidates == 0
        and runtime_changes == 0
        and execution_changes == 0
        and decision == "EMPTY_CANDIDATE_SET_CONFIRMED"
        else "FAIL"
    )

    return {
        "check": "research_candidate_empty_decision",
        "status": status,
        "details": (
            f"decision={decision} "
            f"checks_failed={checks_failed} "
            f"new_strategy_candidates={new_candidates} "
            f"runtime_changes_required={runtime_changes} "
            f"execution_changes_required={execution_changes} "
            f"verdict={verdict}"
        ),
    }


def check_ng_session_filter() -> dict[str, str]:
    path = "src/scripts/research/build_ng_session_filter_hypothesis_v1.py"
    rc, output = run_script(path)
    kv = parse_kv(output)

    pairs_total = as_int(kv.get("pairs_total"))
    symbols_count = as_int(kv.get("symbols_count"))
    positive_sessions = as_int(kv.get("positive_sessions"))
    confirmed_sessions = as_int(kv.get("confirmed_sessions"))
    total_net_pnl = kv.get("total_net_pnl", "0")
    net_pnl_per_pair = kv.get("net_pnl_per_pair", "0")
    verdict = kv.get("VERDICT", "UNKNOWN")

    status = (
        "PASS"
        if rc == 0
        and pairs_total > 0
        and symbols_count >= 1
        and confirmed_sessions == 0
        and verdict in {
            "NG_SESSION_FILTER_HAS_WEAK_SESSION_HYPOTHESIS",
            "NG_SESSION_FILTER_NO_CONFIRMED_EDGE",
        }
        else "FAIL"
    )

    return {
        "check": "ng_session_filter_hypothesis",
        "status": status,
        "details": (
            f"pairs_total={pairs_total} "
            f"symbols_count={symbols_count} "
            f"positive_sessions={positive_sessions} "
            f"confirmed_sessions={confirmed_sessions} "
            f"total_net_pnl={total_net_pnl} "
            f"net_pnl_per_pair={net_pnl_per_pair} "
            f"verdict={verdict}"
        ),
    }


def check_smart_retest_review() -> dict[str, str]:
    path = "src/scripts/research/build_smart_entry_retest_quarantine_apply_plan_review_v1.py"
    rc, output = run_script(path)
    kv = parse_kv(output)

    apply_candidates = as_int(kv.get("apply_candidates"))
    db_update = as_int(kv.get("db_update"))
    already_disabled = as_int(kv.get("already_disabled"))
    no_runtime_match = as_int(kv.get("no_runtime_match"))
    research_only = as_int(kv.get("research_only"))
    require_more_data = as_int(kv.get("require_more_data"))
    verdict = kv.get("VERDICT", "UNKNOWN")

    status = (
        "PASS"
        if rc == 0
        and apply_candidates == 0
        and db_update == 0
        and "NO_DB_CHANGE_REQUIRED" in verdict
        else "FAIL"
    )

    return {
        "check": "smart_entry_retest_quarantine_review",
        "status": status,
        "details": (
            f"apply_candidates={apply_candidates} "
            f"already_disabled={already_disabled} "
            f"no_runtime_match={no_runtime_match} "
            f"research_only={research_only} "
            f"require_more_data={require_more_data} "
            f"db_update={db_update} "
            f"verdict={verdict}"
        ),
    }


def check_candidate_plan() -> dict[str, str]:
    path = "src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py"
    rc, output = run_script(path)
    kv = parse_kv(output)

    promote = as_int(kv.get("promote_to_research_candidate"))
    keep_research_only = as_int(kv.get("keep_research_only"))
    quarantine = as_int(kv.get("quarantine_signal_class"))
    require_more_data = as_int(kv.get("require_more_data"))
    legacy_dirty_data = as_int(kv.get("legacy_dirty_data"))
    verdict = kv.get("VERDICT", "UNKNOWN")

    gold_line = find_line(output, "GOLD_TELEMETRY_GUARD ")
    gold_confirmed = "confirmed=1" in gold_line

    status = (
        "PASS"
        if rc == 0
        and promote == 0
        and not gold_confirmed
        else "FAIL"
    )

    return {
        "check": "signal_class_strategy_candidate_plan",
        "status": status,
        "details": (
            f"promote_to_research_candidate={promote} "
            f"keep_research_only={keep_research_only} "
            f"quarantine_signal_class={quarantine} "
            f"require_more_data={require_more_data} "
            f"legacy_dirty_data={legacy_dirty_data} "
            f"gold_confirmed={1 if gold_confirmed else 0} "
            f"verdict={verdict}"
        ),
    }


def check_trade_context_guard() -> dict[str, str]:
    path = "src/scripts/research/build_trade_context_no_missing_guard_validation_v1.py"

    if not os.path.exists(path):
        return {
            "check": "trade_context_no_missing_guard",
            "status": "SKIP",
            "details": "script_not_found",
        }

    rc, output = run_script(path)
    kv = parse_kv(output)

    strategy_missing = as_int(kv.get("strategy_missing_today"))
    timeframe_missing = as_int(kv.get("timeframe_missing_today"))
    continuous_missing = as_int(kv.get("continuous_symbol_missing_today"))
    discovery_new = as_int(kv.get("discovery_new") or kv.get("unresolved_new_events"))
    verdict = kv.get("VERDICT", "UNKNOWN")

    status = (
        "PASS"
        if rc == 0
        and strategy_missing == 0
        and timeframe_missing == 0
        and continuous_missing == 0
        and discovery_new == 0
        else "FAIL"
    )

    return {
        "check": "trade_context_no_missing_guard",
        "status": status,
        "details": (
            f"strategy_missing_today={strategy_missing} "
            f"timeframe_missing_today={timeframe_missing} "
            f"continuous_symbol_missing_today={continuous_missing} "
            f"discovery_new={discovery_new} "
            f"verdict={verdict}"
        ),
    }


def main() -> int:
    print("=== RESEARCH PAUSE AND ACCUMULATION DECISION V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    checks = [
        check_candidate_plan(),
        check_research_candidate_empty(),
        check_smart_retest_review(),
        check_ng_session_filter(),
        check_trade_context_guard(),
    ]

    failed = [item for item in checks if item["status"] == "FAIL"]
    skipped = [item for item in checks if item["status"] == "SKIP"]

    print("RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_CHECKS")
    for item in checks:
        print(
            "RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_CHECK "
            f"check={item['check']} "
            f"status={item['status']} "
            f"details=\"{item['details']}\""
        )

    print()
    print("RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_SUMMARY")
    print(f"checks_total={len(checks)}")
    print(f"checks_failed={len(failed)}")
    print(f"checks_skipped={len(skipped)}")
    print("new_strategy_candidates=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if failed:
        print("decision=RESEARCH_PAUSE_BLOCKED")
        print("VERDICT=RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_BLOCKED")
        print("RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_V1_FAILED")
        return 1

    print("decision=PAUSE_RESEARCH_AND_ACCUMULATE_DATA")
    print("VERDICT=RESEARCH_PAUSE_AND_ACCUMULATION_CONFIRMED")
    print("RESEARCH_PAUSE_AND_ACCUMULATION_DECISION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
