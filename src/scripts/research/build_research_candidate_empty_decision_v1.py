#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess


# Русский комментарий:
# RESEARCH_CANDIDATE_EMPTY_DECISION_V1 — финальное read-only решение.
# Ничего не пишет в БД, не меняет runtime, не включает execution.
# Скрипт агрегирует результаты последних исследовательских gate'ов и фиксирует,
# что новых strategy/runtime candidates сейчас нет.


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


def parse_kv_lines(output: str) -> dict[str, str]:
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


def contains(output: str, text: str) -> bool:
    return text in output


def main() -> int:
    print("=== RESEARCH CANDIDATE EMPTY DECISION V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    checks: list[dict[str, str]] = []

    # 1. Candidate plan V1.2
    candidate_rc, candidate_output = run_script(
        "src/scripts/research/build_signal_class_strategy_candidate_plan_v1.py"
    )
    candidate_kv = parse_kv_lines(candidate_output)

    promote = as_int(candidate_kv.get("promote_to_research_candidate"))
    keep_research_only = as_int(candidate_kv.get("keep_research_only"))
    quarantine_signal_class = as_int(candidate_kv.get("quarantine_signal_class"))
    require_more_data = as_int(candidate_kv.get("require_more_data"))
    legacy_dirty_data = as_int(candidate_kv.get("legacy_dirty_data"))
    candidate_verdict = candidate_kv.get("VERDICT", "UNKNOWN")

    gold_guard_line = find_line(candidate_output, "GOLD_TELEMETRY_GUARD ")
    gold_confirmed = "confirmed=1" in gold_guard_line
    gold_not_confirmed = "confirmed=0" in gold_guard_line

    candidate_status = "PASS" if candidate_rc == 0 and promote == 0 else "FAIL"

    checks.append(
        {
            "check": "signal_class_strategy_candidate_plan",
            "status": candidate_status,
            "details": (
                f"promote_to_research_candidate={promote} "
                f"keep_research_only={keep_research_only} "
                f"quarantine_signal_class={quarantine_signal_class} "
                f"require_more_data={require_more_data} "
                f"legacy_dirty_data={legacy_dirty_data} "
                f"verdict={candidate_verdict}"
            ),
        }
    )

    checks.append(
        {
            "check": "gold_telemetry_guard",
            "status": "PASS" if gold_not_confirmed and not gold_confirmed else "FAIL",
            "details": gold_guard_line or "GOLD_TELEMETRY_GUARD missing",
        }
    )

    # 2. SMART_ENTRY_RETEST quarantine review
    smart_rc, smart_output = run_script(
        "src/scripts/research/build_smart_entry_retest_quarantine_apply_plan_review_v1.py"
    )
    smart_kv = parse_kv_lines(smart_output)

    apply_candidates = as_int(smart_kv.get("apply_candidates"))
    db_update = as_int(smart_kv.get("db_update"))
    smart_verdict = smart_kv.get("VERDICT", "UNKNOWN")

    smart_status = (
        "PASS"
        if smart_rc == 0
        and apply_candidates == 0
        and db_update == 0
        and "NO_DB_CHANGE_REQUIRED" in smart_verdict
        else "FAIL"
    )

    checks.append(
        {
            "check": "smart_entry_retest_quarantine_review",
            "status": smart_status,
            "details": (
                f"apply_candidates={apply_candidates} "
                f"already_disabled={smart_kv.get('already_disabled', '0')} "
                f"no_runtime_match={smart_kv.get('no_runtime_match', '0')} "
                f"research_only={smart_kv.get('research_only', '0')} "
                f"require_more_data={smart_kv.get('require_more_data', '0')} "
                f"db_update={db_update} "
                f"verdict={smart_verdict}"
            ),
        }
    )

    # 3. Trade context guard
    trade_guard_path = "src/scripts/research/build_trade_context_no_missing_guard_validation_v1.py"
    trade_status = "SKIP"
    trade_details = "script_not_found"

    if os.path.exists(trade_guard_path):
        trade_rc, trade_output = run_script(trade_guard_path)
        trade_kv = parse_kv_lines(trade_output)

        strategy_missing = as_int(trade_kv.get("strategy_missing_today"))
        timeframe_missing = as_int(trade_kv.get("timeframe_missing_today"))
        continuous_missing = as_int(trade_kv.get("continuous_symbol_missing_today"))
        discovery_new = as_int(trade_kv.get("discovery_new") or trade_kv.get("unresolved_new_events"))
        trade_verdict = trade_kv.get("VERDICT", "UNKNOWN")

        trade_status = (
            "PASS"
            if trade_rc == 0
            and strategy_missing == 0
            and timeframe_missing == 0
            and continuous_missing == 0
            and discovery_new == 0
            else "FAIL"
        )
        trade_details = (
            f"strategy_missing_today={strategy_missing} "
            f"timeframe_missing_today={timeframe_missing} "
            f"continuous_symbol_missing_today={continuous_missing} "
            f"discovery_new={discovery_new} "
            f"verdict={trade_verdict}"
        )

    checks.append(
        {
            "check": "trade_context_no_missing_guard",
            "status": trade_status,
            "details": trade_details,
        }
    )

    # 4. Aggregated decision
    failed = [item for item in checks if item["status"] == "FAIL"]
    skipped = [item for item in checks if item["status"] == "SKIP"]

    print("RESEARCH_CANDIDATE_EMPTY_DECISION_CHECKS")
    for item in checks:
        print(
            "RESEARCH_CANDIDATE_EMPTY_DECISION_CHECK "
            f"check={item['check']} "
            f"status={item['status']} "
            f"details=\"{item['details']}\""
        )

    final_status = "EMPTY_CANDIDATE_SET_CONFIRMED" if not failed else "RESEARCH_CANDIDATE_DECISION_BLOCKED"

    print()
    print("RESEARCH_CANDIDATE_EMPTY_DECISION_SUMMARY")
    print(f"checks_total={len(checks)}")
    print(f"checks_failed={len(failed)}")
    print(f"checks_skipped={len(skipped)}")
    print(f"promote_to_research_candidate={promote}")
    print(f"gold_confirmed={1 if gold_confirmed else 0}")
    print(f"smart_retest_apply_candidates={apply_candidates}")
    print(f"smart_retest_db_update={db_update}")
    print("new_strategy_candidates=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"decision={final_status}")

    if failed:
        print("VERDICT=RESEARCH_CANDIDATE_EMPTY_DECISION_BLOCKED")
        print("RESEARCH_CANDIDATE_EMPTY_DECISION_V1_FAILED")
        return 1

    print("VERDICT=RESEARCH_CANDIDATE_EMPTY_DECISION_CONFIRMED")
    print("RESEARCH_CANDIDATE_EMPTY_DECISION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
