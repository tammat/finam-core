#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SYMBOL = os.getenv("SYMBOL", "BRM6@RTSX")
STRATEGY = os.getenv("STRATEGY", "BR_CONSERVATIVE_BREAKOUT")
ROOT = Path(__file__).resolve().parents[3]

REPORTS = [
    ("IDENTITY_GUARD", "src/scripts/research/build_br_strategy_identity_guard_v1.py"),
    ("REPEATABILITY_GATE", "src/scripts/research/build_br_repeatability_gate_v1.py"),
    ("PROFILE_DAY_STABILITY", "src/scripts/research/build_br_profile_day_stability_v1.py"),
    ("GAP_TOXICITY", "src/scripts/research/build_br_gap_toxicity_v2.py"),
    ("SESSION_FILTERED_EDGE", "src/scripts/research/build_br_session_filtered_edge_v1.py"),
    ("CLUSTER_WALKFORWARD", "src/scripts/research/build_br_cluster_walkforward_v1.py"),
    ("RESEARCH_MATURITY", "src/scripts/research/build_br_research_maturity_verdict_v1.py"),
]


KEYWORDS = (
    "status=",
    "verdict=",
    "reason=",
    "trades=",
    "closed=",
    "expectancy=",
    "expectancy_points=",
    "profit_factor=",
    "pf=",
    "winrate=",
    "net_pnl=",
    "max_drawdown=",
    "PASS",
    "FAIL",
    "REJECT",
    "PROMOTE",
    "RESEARCH_ONLY",
    "SHADOW",
)


def run_report(name: str, rel_path: str) -> dict:
    path = ROOT / rel_path
    if not path.exists():
        return {
            "name": name,
            "path": rel_path,
            "ok": False,
            "returncode": 127,
            "summary": ["missing_script"],
        }

    env = dict(os.environ)
    env["SYMBOL"] = SYMBOL
    env["STRATEGY"] = STRATEGY

    try:
        res = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )

        lines = []
        for line in res.stdout.splitlines():
            s = line.strip()
            if any(k in s for k in KEYWORDS):
                lines.append(s)

        if not lines and res.stdout.strip():
            lines = res.stdout.splitlines()[:8]

        if res.stderr.strip():
            lines.extend([f"stderr={x}" for x in res.stderr.splitlines()[:5]])

        return {
            "name": name,
            "path": rel_path,
            "ok": res.returncode == 0,
            "returncode": res.returncode,
            "summary": lines[:30],
        }

    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "path": rel_path,
            "ok": False,
            "returncode": 124,
            "summary": ["timeout_60s"],
        }


def classify(results: list[dict]) -> tuple[str, str]:
    failed = [r for r in results if not r["ok"]]
    text = "\n".join("\n".join(r["summary"]) for r in results).upper()

    if failed:
        return "RESEARCH_ONLY", "one_or_more_source_reports_failed"

    toxic_flags = [
        "FAIL",
        "REJECT",
        "TOXIC",
        "CONTAMINATION",
        "INSUFFICIENT",
        "WEAK",
    ]

    if any(x in text for x in toxic_flags):
        return "RESEARCH_ONLY", "risk_or_insufficient_quality_flags_detected"

    if "PROMOTABLE" in text or "PROMOTE" in text:
        return "SHADOW", "source_reports_allow_shadow_observation"

    return "RESEARCH_ONLY", "no_clear_promotion_signal"


def main() -> int:
    results = [run_report(name, path) for name, path in REPORTS]
    verdict, reason = classify(results)

    print("=== BR EDGE SCORECARD V1 ===")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    print("SOURCE REPORTS")
    for r in results:
        print(
            f"report={r['name']} ok={int(r['ok'])} "
            f"returncode={r['returncode']} path={r['path']}"
        )
        for line in r["summary"]:
            print(f"  {line}")
        print()

    print("EDGE STATUS")
    failed_count = sum(1 for r in results if not r["ok"])
    ok_count = sum(1 for r in results if r["ok"])
    print(f"reports_ok={ok_count}")
    print(f"reports_failed={failed_count}")
    print()

    print("FINAL VERDICT")
    print(f"verdict={verdict}")
    print(f"reason={reason}")

    return 0 if failed_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
