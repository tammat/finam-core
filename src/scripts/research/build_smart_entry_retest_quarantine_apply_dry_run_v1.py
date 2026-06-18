#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess

import psycopg2
import psycopg2.extras


# Русский комментарий:
# SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_V1 — только dry-run.
# Скрипт показывает, какие runtime rows были бы ограничены,
# но не выполняет UPDATE и не меняет runtime_active_universe.


def parse_plan_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in output.splitlines():
        if not line.startswith("SMART_ENTRY_RETEST_QUARANTINE_PLAN_ROW "):
            continue

        row: dict[str, str] = {}
        for part in line.split()[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            row[key] = value

        rows.append(row)

    return rows


def load_runtime_rows() -> list[dict[str, str]]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return []

    # SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_V1_SCHEMA_SAFE_RUNTIME_ACTIVE_UNIVERSE
    # Русский комментарий:
    # runtime_active_universe в текущей схеме не имеет колонки continuous_symbol.
    # Поэтому continuous_symbol извлекаем из raw_json при наличии, иначе оставляем пустым.
    sql = """
    SELECT
        symbol,
        strategy,
        timeframe,
        is_enabled,
        disable_reason,
        updated_at,
        raw_json
    FROM runtime_active_universe
    ORDER BY strategy, timeframe, symbol
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]

    for row in rows:
        raw_json = row.get("raw_json")
        continuous_symbol = ""

        if isinstance(raw_json, dict):
            continuous_symbol = (
                raw_json.get("continuous_symbol")
                or raw_json.get("root_symbol")
                or raw_json.get("symbol")
                or ""
            )

        row["continuous_symbol"] = continuous_symbol

    return rows


def normalize(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def runtime_match_score(plan: dict[str, str], runtime: dict[str, str]) -> int:
    # SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_V1_1_STRICT_MATCHING
    # Русский комментарий:
    # Без совпадения strategy runtime row не считается кандидатом.
    # Иначе возникают ложные совпадения по timeframe, например USDRUB -> BRM6 или NG -> NVTK.
    plan_strategy = normalize(plan.get("strategy"))
    runtime_strategy = normalize(runtime.get("strategy"))

    if not plan_strategy or plan_strategy != runtime_strategy:
        return 0

    score = 10

    plan_timeframe = normalize(plan.get("timeframe"))
    runtime_timeframe = normalize(runtime.get("timeframe"))

    if plan_timeframe and plan_timeframe == runtime_timeframe:
        score += 5

    plan_cont = normalize(plan.get("continuous_symbol"))
    runtime_cont = normalize(runtime.get("continuous_symbol"))
    runtime_symbol = normalize(runtime.get("symbol"))

    if plan_cont and runtime_cont and plan_cont == runtime_cont:
        score += 5

    # Русский комментарий:
    # continuous_symbol может отсутствовать в runtime_active_universe,
    # поэтому допускаем только явную близость continuous root к symbol.
    if plan_cont and runtime_symbol:
        plan_root = plan_cont.replace("_CONT", "").replace("@RTSX", "").replace("@MISX", "")
        if plan_root and runtime_symbol.upper().startswith(plan_root.upper()):
            score += 2

    return score


def planned_disable_reason(plan: dict[str, str]) -> str:
    reason = normalize(plan.get("reason")) or "smart_entry_retest_quarantine"
    return f"SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN:{reason}"


def main() -> int:
    print("=== SMART ENTRY RETEST QUARANTINE APPLY DRY RUN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    proc = subprocess.run(
        ["python3", "src/scripts/research/build_smart_entry_retest_quarantine_plan_v1.py"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_FAILED_PLAN")
        return proc.returncode

    plan_rows = parse_plan_rows(proc.stdout)
    runtime_rows = load_runtime_rows()

    print("SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_ROWS")

    planned_changes = 0
    quarantine_candidates = 0
    session_filter_candidates = 0
    require_more_data = 0
    no_runtime_match = 0

    for plan in plan_rows:
        action = normalize(plan.get("planned_action"))
        strategy = normalize(plan.get("strategy"))
        timeframe = normalize(plan.get("timeframe"))
        continuous_symbol = normalize(plan.get("continuous_symbol"))

        if action == "QUARANTINE_RUNTIME_CANDIDATE":
            quarantine_candidates += 1
        elif action == "RESEARCH_ONLY_WITH_SESSION_FILTER":
            session_filter_candidates += 1
        elif action == "REQUIRE_MORE_DATA":
            require_more_data += 1

        matches = sorted(
            (
                (runtime_match_score(plan, runtime), runtime)
                for runtime in runtime_rows
            ),
            key=lambda x: x[0],
            reverse=True,
        )

        best_score = matches[0][0] if matches else 0
        best_runtime = matches[0][1] if matches and best_score > 0 else None

        would_change = False
        target_enabled = None
        target_reason = ""

        if action == "QUARANTINE_RUNTIME_CANDIDATE":
            if best_runtime and best_score >= 10:
                runtime_enabled = normalize(best_runtime.get("is_enabled")).lower() in {"true", "t", "1", "yes"}
                if runtime_enabled:
                    would_change = True
                    target_enabled = False
                    target_reason = planned_disable_reason(plan)
                    planned_changes += 1
                else:
                    # Русский комментарий:
                    # Строка уже disabled, поэтому это подтверждённый match, но не изменение.
                    target_enabled = False
                    target_reason = "ALREADY_DISABLED"
            else:
                no_runtime_match += 1

        elif action == "RESEARCH_ONLY_WITH_SESSION_FILTER":
            # Русский комментарий:
            # Для NG пока не отключаем runtime в dry-run, а фиксируем необходимость
            # session-filter/research-only правила.
            target_reason = planned_disable_reason(plan)

        print(
            "SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_ROW "
            f"family={plan.get('family', 'UNKNOWN')} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"continuous_symbol={continuous_symbol} "
            f"pairs={plan.get('pairs', '0')} "
            f"winrate={plan.get('winrate', '0')} "
            f"net_pnl={plan.get('net_pnl', '0')} "
            f"net_pnl_per_pair={plan.get('net_pnl_per_pair', '0')} "
            f"planned_action={action} "
            f"reason={plan.get('reason', 'UNKNOWN')} "
            f"runtime_match_score={best_score} "
            f"runtime_symbol={normalize(best_runtime.get('symbol')) if best_runtime else 'NONE'} "
            f"runtime_strategy={normalize(best_runtime.get('strategy')) if best_runtime else 'NONE'} "
            f"runtime_timeframe={normalize(best_runtime.get('timeframe')) if best_runtime else 'NONE'} "
            f"runtime_continuous_symbol={normalize(best_runtime.get('continuous_symbol')) if best_runtime else 'NONE'} "
            f"runtime_is_enabled={normalize(best_runtime.get('is_enabled')) if best_runtime else 'NONE'} "
            f"would_change={1 if would_change else 0} "
            f"target_enabled={target_enabled if target_enabled is not None else 'UNCHANGED'} "
            f"target_disable_reason={target_reason if target_reason else 'NONE'}"
        )

    print()
    print("SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_SUMMARY")
    print(f"plan_rows={len(plan_rows)}")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"quarantine_runtime_candidates={quarantine_candidates}")
    print(f"session_filter_candidates={session_filter_candidates}")
    print(f"require_more_data={require_more_data}")
    print(f"planned_changes={planned_changes}")
    print(f"no_runtime_match={no_runtime_match}")
    print("db_update=0")

    if len(plan_rows) == 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_EMPTY")
    elif quarantine_candidates > 0 and planned_changes == 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_NO_RUNTIME_MATCH")
    elif planned_changes > 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_READY")
    else:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_RESEARCH_ONLY")

    print("SMART_ENTRY_RETEST_QUARANTINE_APPLY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
