#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import date
import psycopg2
import psycopg2.extras


FUTURES_REAL_ALLOWED_AFTER = date(2026, 7, 1)


def env_value(name: str) -> str:
    return str(os.environ.get(name, "")).strip()


def boolish(value: str) -> str:
    v = str(value or "").strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return "1"
    if v in {"0", "false", "f", "no", "n", "off", ""}:
        return "0"
    return v


def table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        select exists (
            select 1
            from information_schema.tables
            where table_schema='public'
              and table_name=%s
        ) as exists;
        """,
        (name,),
    )
    return bool(cur.fetchone()["exists"])


def fetch_operational_metrics(cur) -> dict:
    cur.execute("select * from clean_operational_position_metrics_v1;")
    row = cur.fetchone()
    return dict(row) if row else {}


def fetch_runtime_enabled_rows(cur) -> list[dict]:
    if not table_exists(cur, "runtime_active_universe"):
        return []

    cur.execute(
        """
        select *
        from runtime_active_universe
        where coalesce(is_enabled,false)=true
        order by symbol;
        """
    )
    return [dict(r) for r in cur.fetchall()]


def main() -> int:
    print("=== LIMITED REAL DRY RUN READINESS REVIEW V1 ===")
    print("mode=diagnostic_review")
    print("runtime_allow=0")
    print("execution_enabled=0")

    today = date.today()
    futures_real_block_active = today < FUTURES_REAL_ALLOWED_AFTER

    env_names = [
        "EXECUTION_MODE",
        "EXECUTION_ENABLED",
        "REAL_TRADING_ENABLED",
        "ENABLE_REAL_EXECUTION",
        "RUNTIME_ALLOW",
        "RUNTIME_ALLOWED",
        "DRY_RUN",
        "BROKER_DRY_RUN",
        "FINAM_DRY_RUN",
        "ENABLE_PROTECTIVE_ORDERS",
        "ENABLE_SYNTHETIC_PROTECTIVE",
        "DAILY_LOSS_LIMIT",
        "MAX_RISK_PER_TRADE",
        "ENABLE_KILL_SWITCH",
    ]

    env = {name: env_value(name) for name in env_names}

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            metrics = fetch_operational_metrics(cur)
            runtime_enabled = fetch_runtime_enabled_rows(cur)

            table_flags = {
                "runtime_active_universe": table_exists(cur, "runtime_active_universe"),
                "clean_operational_position_view_v1": table_exists(cur, "clean_operational_position_view_v1"),
                "clean_operational_position_metrics_v1": table_exists(cur, "clean_operational_position_metrics_v1"),
                "trades": table_exists(cur, "trades"),
                "closed_trade_chains_v3": table_exists(cur, "closed_trade_chains_v3"),
            }

    print()
    print("DRY_RUN_ENV_FLAGS")
    for name in env_names:
        print(f"ENV_FLAG name={name} value={env[name] or '<EMPTY>'}")

    print()
    print("DRY_RUN_TABLE_FLAGS")
    for name, exists in table_flags.items():
        print(f"TABLE_FLAG table={name} exists={int(exists)}")

    print()
    print(
        "DRY_RUN_OPERATIONAL_METRICS "
        f"current_position_count={metrics.get('current_position_count')} "
        f"clean_flat_count={metrics.get('clean_flat_count')} "
        f"clean_open_review_count={metrics.get('clean_open_review_count')} "
        f"quarantine_count={metrics.get('quarantine_count')} "
        f"excluded_count={metrics.get('excluded_count')} "
        f"current_net_qty_sum={metrics.get('current_net_qty_sum')} "
        f"included_rows={metrics.get('included_rows')} "
        f"included_v3_pnl={metrics.get('included_v3_pnl')}"
    )

    print()
    print("DRY_RUN_RUNTIME_ENABLED_ROWS")
    if not runtime_enabled:
        print("RUNTIME_ENABLED_ROWS=0")
    else:
        for r in runtime_enabled:
            fields = []
            for k in ["symbol", "strategy", "timeframe", "is_enabled", "runtime_allowed", "execution_enabled", "source", "priority"]:
                if k in r:
                    fields.append(f"{k}={r[k]}")
            print("RUNTIME_ENABLED_ROW " + " ".join(fields))

    blockers: list[str] = []
    warnings: list[str] = []

    # Hard blockers: real execution must be off.
    if boolish(env.get("EXECUTION_ENABLED", "")) == "1":
        blockers.append("EXECUTION_ENABLED_IS_ON")

    if boolish(env.get("REAL_TRADING_ENABLED", "")) == "1":
        blockers.append("REAL_TRADING_ENABLED_IS_ON")

    if boolish(env.get("ENABLE_REAL_EXECUTION", "")) == "1":
        blockers.append("ENABLE_REAL_EXECUTION_IS_ON")

    # Futures real trading date block.
    if futures_real_block_active:
        blockers.append("FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01")

    # Operational blockers.
    if int(metrics.get("quarantine_count") or 0) > 0:
        warnings.append("HAS_QUARANTINE_ROWS")

    if int(metrics.get("excluded_count") or 0) > 0:
        warnings.append("HAS_EXCLUDED_ROWS")

    if int(metrics.get("current_position_count") or 0) > 0:
        warnings.append("HAS_OPEN_PAPER_POSITION_TAIL")

    # Dry-run flag is allowed to be absent, but then dry-run review is not formally ready.
    dry_run_flags = [
        boolish(env.get("DRY_RUN", "")),
        boolish(env.get("BROKER_DRY_RUN", "")),
        boolish(env.get("FINAM_DRY_RUN", "")),
    ]
    if "1" not in dry_run_flags:
        warnings.append("NO_EXPLICIT_BROKER_DRY_RUN_FLAG_VISIBLE")

    # Protective/risk guards visibility.
    if not env.get("DAILY_LOSS_LIMIT"):
        warnings.append("DAILY_LOSS_LIMIT_NOT_VISIBLE_IN_ENV")

    if not env.get("MAX_RISK_PER_TRADE"):
        warnings.append("MAX_RISK_PER_TRADE_NOT_VISIBLE_IN_ENV")

    if boolish(env.get("ENABLE_KILL_SWITCH", "")) != "1":
        warnings.append("KILL_SWITCH_ENV_FLAG_NOT_VISIBLE_OR_OFF")

    print()
    print("DRY_RUN_READINESS_CLASSIFICATION")
    print("research_ready=1")
    print("paper_ready=1")
    print("shadow_ready=1")
    print("limited_real_dry_run_review_ready=0")
    print("real_execution_ready=0")
    print("production_trading_ready=0")
    print(f"futures_real_block_active={int(futures_real_block_active)}")
    print(f"futures_real_allowed_after={FUTURES_REAL_ALLOWED_AFTER.isoformat()}")

    print()
    print(f"warnings_count={len(warnings)}")
    print("WARNINGS=" + (",".join(warnings) if warnings else "none"))

    print(f"blockers_count={len(blockers)}")
    print("BLOCKERS=" + (",".join(blockers) if blockers else "none"))

    if blockers:
        print("VERDICT=NOT_READY_FOR_LIMITED_REAL_DRY_RUN")
    else:
        print("VERDICT=READY_FOR_LIMITED_REAL_DRY_RUN_REVIEW_WITH_WARNINGS")

    print("LIMITED_REAL_DRY_RUN_READINESS_REVIEW_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
