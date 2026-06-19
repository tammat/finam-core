#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_VOLATILITY_GATE_CALLSITE_AUDIT_V1
# Read-only аудит callsite-ов BR/futures volatility gate.
# Цель — найти точное место, где equity path использует BR volatility gate,
# прежде чем делать patch.


ROOT = Path(".").resolve()

TARGET_FILES = [
    Path("src/finam_core/pipelines/paper_pipeline.py"),
    Path("src/finam_core/risk/br_adaptive_volatility_gate.py"),
    Path("src/finam_core/risk/br_compression_watch.py"),
    Path("src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py"),
    Path("src/finam_core/strategy/equities/volatility_breakout_equity.py"),
    Path("src/finam_core/strategy/strategy_factory.py"),
]

TERMS = [
    "br_adaptive_volatility_gate",
    "BrAdaptiveVolatilityGate",
    "br_volatility_too_low",
    "br_volatility_ok",
    "high_vol_static_cap",
    "low_vol_adaptive",
    "compression_watch_active",
    "_save_pre_signal_block_audit_v1",
    "runtime_guard_pre_signal_block_audit_v1",
    "VOLATILITY_BREAKOUT_EQUITY",
    "symbol.endswith(\"@MISX\")",
    "@MISX",
]


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []


def emit_context(path: Path, line_no: int, lines: list[str], term: str) -> None:
    start = max(1, line_no - 4)
    end = min(len(lines), line_no + 4)

    print(
        "EQUITY_VOL_GATE_CALLSITE_HIT "
        f"file={path} "
        f"line={line_no} "
        f"term={term}"
    )

    for idx in range(start, end + 1):
        code = lines[idx - 1].strip()
        print(
            "EQUITY_VOL_GATE_CALLSITE_CONTEXT "
            f"file={path} "
            f"line={idx} "
            f"code={code}"
        )


def main() -> int:
    print("=== EQUITY VOLATILITY GATE CALLSITE AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"root={ROOT}")
    print()

    hits = []

    for rel in TARGET_FILES:
        path = ROOT / rel
        lines = read_lines(path)

        if not lines:
            print(f"EQUITY_VOL_GATE_CALLSITE_FILE_MISSING file={rel}")
            continue

        for line_no, line in enumerate(lines, start=1):
            for term in TERMS:
                if term in line:
                    hits.append((rel, line_no, term))
                    emit_context(rel, line_no, lines, term)

    files_with_hits = len({h[0] for h in hits})
    br_gate_hits = len([h for h in hits if h[2] in {"br_adaptive_volatility_gate", "BrAdaptiveVolatilityGate", "br_volatility_too_low", "br_volatility_ok"}])
    equity_hits = len([h for h in hits if h[2] in {"VOLATILITY_BREAKOUT_EQUITY", "symbol.endswith(\"@MISX\")", "@MISX"}])
    audit_writer_hits = len([h for h in hits if h[2] in {"_save_pre_signal_block_audit_v1", "runtime_guard_pre_signal_block_audit_v1"}])

    print()
    print("EQUITY_VOLATILITY_GATE_CALLSITE_AUDIT_SUMMARY")
    print(f"files_with_hits={files_with_hits}")
    print(f"hits_total={len(hits)}")
    print(f"br_gate_hits={br_gate_hits}")
    print(f"equity_hits={equity_hits}")
    print(f"audit_writer_hits={audit_writer_hits}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if br_gate_hits > 0 and equity_hits > 0:
        print("VERDICT=EQUITY_VOLATILITY_GATE_CALLSITE_FOUND")
    elif br_gate_hits > 0:
        print("VERDICT=BR_GATE_FOUND_EQUITY_ROUTE_REVIEW_REQUIRED")
    else:
        print("VERDICT=BR_GATE_CALLSITE_NOT_FOUND")

    print("EQUITY_VOLATILITY_GATE_CALLSITE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
