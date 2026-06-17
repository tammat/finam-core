#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


RUNTIME_TABLE_CANDIDATES = [
    "runtime_active_universe",
    "runtime_worker_state",
    "runtime_governance_state",
    "research_runtime_state",
]


def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        select exists (
            select 1
            from information_schema.tables
            where table_schema='public'
              and table_name=%s
        ) as exists;
        """,
        (table_name,),
    )
    return bool(cur.fetchone()["exists"])


def fetch_table_columns(cur, table_name: str) -> set[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s;
        """,
        (table_name,),
    )
    return {r["column_name"] for r in cur.fetchall()}


def fetch_runtime_active_universe(cur) -> list[dict]:
    if not table_exists(cur, "runtime_active_universe"):
        return []

    cols = fetch_table_columns(cur, "runtime_active_universe")

    select_cols = ["symbol"]
    for c in [
        "strategy",
        "timeframe",
        "is_enabled",
        "runtime_allowed",
        "execution_enabled",
        "source",
        "priority",
        "updated_at",
        "created_at",
    ]:
        if c in cols:
            select_cols.append(c)

    sql = f"""
        select {", ".join(select_cols)}
        from runtime_active_universe
        order by symbol;
    """
    cur.execute(sql)
    return [dict(r) for r in cur.fetchall()]


def fetch_operational_rows(cur) -> list[dict]:
    cur.execute(
        """
        select
            symbol,
            strategy,
            timeframe,
            net_qty,
            full_chains,
            v3_pnl,
            operational_status,
            is_current_operational_position,
            include_in_clean_operational_view
        from clean_operational_position_view_v1
        order by operational_status, symbol, strategy, timeframe;
        """
    )
    return [dict(r) for r in cur.fetchall()]


def env_flag(name: str) -> str:
    return str(os.environ.get(name, "")).strip()


def normalize_boolish(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return "1"
    if text in {"0", "false", "f", "no", "n", "off"}:
        return "0"
    return str(value)


def main() -> int:
    print("=== RUNTIME OPERATIONAL GOVERNANCE ALIGNMENT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    database_url = os.environ["DATABASE_URL"]

    with psycopg2.connect(database_url) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            operational_rows = fetch_operational_rows(cur)
            runtime_rows = fetch_runtime_active_universe(cur)

            existing_tables = {}
            for t in RUNTIME_TABLE_CANDIDATES:
                existing_tables[t] = table_exists(cur, t)

    runtime_by_symbol = {}
    for row in runtime_rows:
        runtime_by_symbol.setdefault(row["symbol"], []).append(row)

    print()
    print("RUNTIME_TABLES")
    for name, exists in existing_tables.items():
        print(f"RUNTIME_TABLE_ROW table={name} exists={int(exists)}")

    print()
    print("ENV_GOVERNANCE_FLAGS")
    for name in [
        "EXECUTION_ENABLED",
        "REAL_TRADING_ENABLED",
        "RUNTIME_ALLOW",
        "RUNTIME_ALLOWED",
        "ENABLE_REAL_EXECUTION",
        "ENABLE_RUNTIME_SYMBOL_RELOAD",
        "ENABLE_NG_PAPER_ACCUMULATION_BYPASS_V1",
        "ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1",
        "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1",
    ]:
        print(f"ENV_FLAG name={name} value={env_flag(name) or '<EMPTY>'}")

    print()
    print("OPERATIONAL_ROWS")
    for r in operational_rows:
        print(
            "OPERATIONAL_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"net_qty={r['net_qty']} "
            f"full_chains={r['full_chains']} "
            f"pnl={r['v3_pnl']} "
            f"status={r['operational_status']} "
            f"current_position={int(r['is_current_operational_position'])} "
            f"include_clean={int(r['include_in_clean_operational_view'])}"
        )

    print()
    print("RUNTIME_ACTIVE_UNIVERSE_ROWS")
    if not runtime_rows:
        print("RUNTIME_ACTIVE_UNIVERSE_EMPTY_OR_MISSING=1")
    else:
        for r in runtime_rows:
            fields = []
            for k in [
                "symbol",
                "strategy",
                "timeframe",
                "is_enabled",
                "runtime_allowed",
                "execution_enabled",
                "source",
                "priority",
            ]:
                if k in r:
                    fields.append(f"{k}={r[k]}")
            print("RUNTIME_ACTIVE_ROW " + " ".join(fields))

    blockers: list[str] = []
    warnings: list[str] = []

    # Hard governance: real execution flags must remain off.
    hard_off_flags = [
        "EXECUTION_ENABLED",
        "REAL_TRADING_ENABLED",
        "ENABLE_REAL_EXECUTION",
    ]
    for name in hard_off_flags:
        value = normalize_boolish(env_flag(name))
        if value == "1":
            blockers.append(f"{name}_IS_ENABLED")

    # Operational quarantine/excluded must not be enabled for runtime/execution.
    for r in operational_rows:
        symbol = r["symbol"]
        status = r["operational_status"]
        runtime_matches = runtime_by_symbol.get(symbol, [])

        if status in {"QUARANTINE_CONTAMINATED_TAIL", "EXCLUDE_HISTORICAL_TAIL"}:
            for rr in runtime_matches:
                is_enabled = normalize_boolish(rr.get("is_enabled"))
                runtime_allowed = normalize_boolish(rr.get("runtime_allowed"))
                execution_enabled = normalize_boolish(rr.get("execution_enabled"))

                if is_enabled == "1" or runtime_allowed == "1" or execution_enabled == "1":
                    blockers.append(
                        f"{symbol}_{status}_PRESENT_IN_ACTIVE_RUNTIME"
                    )

        if status == "OPEN_PAPER_LONG_TAIL":
            if symbol != "BRN6@RTSX":
                warnings.append(f"{symbol}_OPEN_TAIL_UNEXPECTED")
            if not runtime_matches:
                warnings.append(f"{symbol}_OPEN_TAIL_NOT_IN_RUNTIME_UNIVERSE")
            else:
                for rr in runtime_matches:
                    execution_enabled = normalize_boolish(rr.get("execution_enabled"))
                    if execution_enabled == "1":
                        blockers.append(f"{symbol}_OPEN_TAIL_EXECUTION_ENABLED")

        if status in {"CLEAN_V3_FLAT", "CLEAN_V3_OPEN_REVIEW"}:
            for rr in runtime_matches:
                execution_enabled = normalize_boolish(rr.get("execution_enabled"))
                if execution_enabled == "1":
                    blockers.append(f"{symbol}_CLEAN_ROW_EXECUTION_ENABLED")

    # Explicit expected quarantine/excluded symbols.
    for symbol in ["USDRUBF@RTSX", "BRM6@RTSX"]:
        matches = runtime_by_symbol.get(symbol, [])
        for rr in matches:
            is_enabled = normalize_boolish(rr.get("is_enabled"))
            runtime_allowed = normalize_boolish(rr.get("runtime_allowed"))
            execution_enabled = normalize_boolish(rr.get("execution_enabled"))
            if is_enabled == "1" or runtime_allowed == "1" or execution_enabled == "1":
                blockers.append(f"{symbol}_MUST_NOT_BE_RUNTIME_ACTIVE")

    print()
    print("ALIGNMENT_SUMMARY")
    print(f"operational_rows={len(operational_rows)}")
    print(f"runtime_active_rows={len(runtime_rows)}")
    print(f"blockers_count={len(blockers)}")
    print(f"warnings_count={len(warnings)}")

    if warnings:
        print("WARNINGS=" + ",".join(warnings))
    else:
        print("WARNINGS=none")

    if blockers:
        print("BLOCKERS=" + ",".join(blockers))
        print("VERDICT=RUNTIME_OPERATIONAL_GOVERNANCE_MISALIGNED")
        raise SystemExit(1)

    print("BLOCKERS=none")
    print("VERDICT=RUNTIME_OPERATIONAL_GOVERNANCE_ALIGNED_READONLY")
    print("RUNTIME_OPERATIONAL_GOVERNANCE_ALIGNMENT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
