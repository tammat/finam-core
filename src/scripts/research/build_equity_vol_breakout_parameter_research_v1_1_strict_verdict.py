#!/usr/bin/env python3
# Русский комментарий: строгая интерпретация V1 — отрицательный expectancy не может быть кандидатом.

import subprocess
import sys
import re

def main() -> int:
    print("=== EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1_1_STRICT_VERDICT ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")

    result = subprocess.run(
        [sys.executable, "src/scripts/research/build_equity_vol_breakout_parameter_research_v1.py"],
        text=True,
        capture_output=True,
        check=False,
    )

    print(result.stdout, end="")

    if result.returncode != 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_PARAMETER_RESEARCH_V1_FAILED")
        return 1

    best = None
    for line in result.stdout.splitlines():
        if line.startswith("BEST_ROW "):
            best = line
            break

    if not best:
        print("STRICT_SUMMARY best_row_found=0")
        print("VERDICT=EQUITY_VOL_BREAKOUT_NO_VALID_RESULT")
        return 1

    exp_match = re.search(r"expectancy_5=([\-0-9.]+)", best)
    pf_match = re.search(r"profit_factor_5=([\-0-9.]+)", best)
    sig_match = re.search(r"signals=([0-9]+)", best)

    expectancy = float(exp_match.group(1)) if exp_match else 0.0
    profit_factor = float(pf_match.group(1)) if pf_match else 0.0
    signals = int(sig_match.group(1)) if sig_match else 0

    positive_edge = expectancy > 0 and profit_factor >= 1.2 and signals >= 100

    print("")
    print("STRICT_SUMMARY")
    print(f"best_expectancy_5={expectancy}")
    print(f"best_profit_factor_5={profit_factor}")
    print(f"best_signals={signals}")
    print(f"positive_edge={int(positive_edge)}")
    print("min_profit_factor_required=1.2")
    print("min_signals_required=100")

    if positive_edge:
        print("VERDICT=EQUITY_VOL_BREAKOUT_POSITIVE_EDGE_CANDIDATE")
        return 0

    print("VERDICT=EQUITY_VOL_BREAKOUT_NO_POSITIVE_EDGE")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
