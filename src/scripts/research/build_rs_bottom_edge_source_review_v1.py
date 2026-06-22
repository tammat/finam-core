#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import subprocess
from decimal import Decimal


SYMBOL_SCRIPT = "src/scripts/research/build_rs_bottom_symbol_scorecard_v1.py"
FAMILY_SCRIPT = "src/scripts/research/build_rs_bottom_family_scorecard_v1.py"


def run_script(path: str) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    p = subprocess.run(
        ["python3", path],
        cwd="/opt/finam-core",
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )

    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout)

    return p.stdout


def dec(x):
    if x in (None, "None", ""):
        return None
    return Decimal(str(x))


def parse_rows(raw: str, prefix: str) -> list[dict]:
    rows = []
    for line in raw.splitlines():
        if not line.startswith(prefix):
            continue

        d = {}
        for k, v in re.findall(r"(\w+)=([^ ]+)", line):
            d[k] = v

        pf = dec(d.get("profit_factor"))
        obs = int(d.get("observations", "0"))

        if pf is None or obs < 30:
            continue

        d["profit_factor_decimal"] = pf
        d["observations_int"] = obs
        rows.append(d)

    return rows


def classify(symbol_rows: list[dict], family_rows: list[dict]) -> str:
    top_symbol = max(symbol_rows, key=lambda r: r["profit_factor_decimal"], default=None)
    top_family = max(family_rows, key=lambda r: r["profit_factor_decimal"], default=None)

    if not top_symbol or not top_family:
        return "EDGE_SOURCE_NO_DATA"

    symbol = top_symbol.get("symbol", "")
    family = top_family.get("family", "")

    if symbol.startswith("BR") and family == "BRENT":
        return "BRENT_DOMINATES"
    if symbol.startswith("NG") and family == "GAS":
        return "GAS_DOMINATES"
    if (symbol.startswith("GD") or symbol.startswith("GL")) and family == "GOLD":
        return "GOLD_DOMINATES"
    if symbol.startswith("SV") and family == "SILVER":
        return "SILVER_DOMINATES"

    if top_symbol["profit_factor_decimal"] >= Decimal("3.0") and top_family["profit_factor_decimal"] < Decimal("1.5"):
        return "CONTRACT_SPECIFIC_ANOMALY"

    return "DIVERSIFIED_EDGE"


def main() -> int:
    print("=== RS_BOTTOM_EDGE_SOURCE_REVIEW_V1 ===")
    print("mode=research_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    symbol_raw = run_script(SYMBOL_SCRIPT)
    family_raw = run_script(FAMILY_SCRIPT)

    symbol_rows = parse_rows(symbol_raw, "RS_BOTTOM_SYMBOL_ROW")
    family_rows = parse_rows(family_raw, "RS_BOTTOM_FAMILY_ROW")

    top_symbols = sorted(
        symbol_rows,
        key=lambda r: (r["profit_factor_decimal"], r["observations_int"]),
        reverse=True,
    )[:10]

    top_families = sorted(
        family_rows,
        key=lambda r: (r["profit_factor_decimal"], r["observations_int"]),
        reverse=True,
    )[:10]

    for r in top_symbols:
        print(
            "EDGE_SOURCE_SYMBOL "
            f"symbol={r.get('symbol')} "
            f"selection={r.get('selection')} "
            f"filter={r.get('filter')} "
            f"horizon_min={r.get('horizon_min')} "
            f"observations={r.get('observations')} "
            f"winrate={r.get('winrate')} "
            f"avg_return_pct={r.get('avg_return_pct')} "
            f"profit_factor={r.get('profit_factor')}"
        )

    for r in top_families:
        print(
            "EDGE_SOURCE_FAMILY "
            f"family={r.get('family')} "
            f"selection={r.get('selection')} "
            f"filter={r.get('filter')} "
            f"horizon_min={r.get('horizon_min')} "
            f"symbols={r.get('symbols')} "
            f"observations={r.get('observations')} "
            f"winrate={r.get('winrate')} "
            f"avg_return_pct={r.get('avg_return_pct')} "
            f"profit_factor={r.get('profit_factor')}"
        )

    verdict = classify(symbol_rows, family_rows)

    print(f"symbol_rows={len(symbol_rows)}")
    print(f"family_rows={len(family_rows)}")
    print(f"edge_source_verdict={verdict}")

    if symbol_rows and family_rows:
        print("VERDICT=RS_BOTTOM_EDGE_SOURCE_REVIEW_READY")
    else:
        print("VERDICT=RS_BOTTOM_EDGE_SOURCE_REVIEW_NO_DATA")

    print("TEST_RS_BOTTOM_EDGE_SOURCE_REVIEW_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
