#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import sys
from decimal import Decimal
from collections import defaultdict


BASE_SCRIPT = "src/scripts/research/build_futures_relative_strength_layer_v1.py"

M1_WEIGHT = Decimal("0.4")
M5_WEIGHT = Decimal("0.6")


def parse_base_rows(raw: str) -> list[dict]:
    rows = []

    for line in raw.splitlines():
        if not line.startswith("FUTURES_RS_ROW "):
            continue

        item = {}
        for part in line.split()[1:]:
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            item[k] = v

        if item:
            rows.append(item)

    return rows


def dec(value: str | None) -> Decimal:
    if value in (None, "", "None"):
        return Decimal("0")
    return Decimal(str(value))


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    proc = subprocess.run(
        [sys.executable, BASE_SCRIPT],
        cwd="/opt/finam-core",
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(proc.returncode)

    base_rows = parse_base_rows(proc.stdout)

    grouped = defaultdict(dict)
    for r in base_rows:
        symbol = r.get("symbol")
        timeframe = r.get("timeframe")
        if not symbol or timeframe not in {"M1", "M5"}:
            continue
        grouped[symbol][timeframe] = r

    normalized = []

    for symbol, tf_rows in grouped.items():
        m1 = tf_rows.get("M1")
        m5 = tf_rows.get("M5")

        rs_m1 = dec(m1.get("return_pct")) if m1 else None
        rs_m5 = dec(m5.get("return_pct")) if m5 else None

        if rs_m1 is not None and rs_m5 is not None:
            rs_score = rs_m1 * M1_WEIGHT + rs_m5 * M5_WEIGHT
        elif rs_m5 is not None:
            rs_score = rs_m5
        elif rs_m1 is not None:
            rs_score = rs_m1
        else:
            continue

        latest_ts = None
        if m1 and m5:
            latest_ts = max(m1.get("last_ts", ""), m5.get("last_ts", ""))
        elif m1:
            latest_ts = m1.get("last_ts")
        elif m5:
            latest_ts = m5.get("last_ts")

        family = (m5 or m1 or {}).get("family", "OTHER")
        last_close = (m1 or m5 or {}).get("last_close")

        normalized.append({
            "symbol": symbol,
            "family": family,
            "rs_m1": str(rs_m1) if rs_m1 is not None else None,
            "rs_m5": str(rs_m5) if rs_m5 is not None else None,
            "rs_score": str(rs_score),
            "last_close": last_close,
            "last_ts": latest_ts,
        })

    normalized.sort(key=lambda r: dec(r["rs_score"]), reverse=True)

    for i, r in enumerate(normalized, start=1):
        r["rank"] = i

    leaders = normalized[:5]
    laggards = normalized[-5:] if normalized else []

    out = {
        "verdict": "FUTURES_RELATIVE_STRENGTH_FAMILY_NORMALIZED_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "base_rows": len(base_rows),
        "normalized_rows": len(normalized),
        "leaders": [r["symbol"] for r in leaders],
        "laggards": [r["symbol"] for r in laggards],
        "rows": normalized,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    for r in normalized:
        print(
            "FUTURES_RS_NORMALIZED_ROW "
            f"rank={r['rank']} "
            f"symbol={r['symbol']} "
            f"family={r['family']} "
            f"rs_m1={r['rs_m1']} "
            f"rs_m5={r['rs_m5']} "
            f"rs_score={r['rs_score']} "
            f"last_close={r['last_close']} "
            f"last_ts={r['last_ts']}",
            flush=True,
        )

    print("FUTURES_RS_NORMALIZED_LEADERS " + ",".join(r["symbol"] for r in leaders))
    print("FUTURES_RS_NORMALIZED_LAGGARDS " + ",".join(r["symbol"] for r in laggards))
    print("VERDICT=FUTURES_RELATIVE_STRENGTH_FAMILY_NORMALIZED_READY")
    print("TEST_FUTURES_RELATIVE_STRENGTH_FAMILY_NORMALIZED_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
