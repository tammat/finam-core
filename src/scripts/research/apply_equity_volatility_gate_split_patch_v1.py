#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_VOLATILITY_GATE_SPLIT_PATCH_V1
# Узкий patch для paper_pipeline:
# - @MISX получает EQUITY_ATR_MIN_PCT вместо ATR_MIN_PCT.
# - audit reason br_volatility_too_low переименуется в equity_volatility_too_low.
# - BR/futures логика не меняется.
# - real execution не включается.


PATH = Path("src/finam_core/pipelines/paper_pipeline.py")


def main() -> int:
    text = PATH.read_text(encoding="utf-8")

    old_threshold = 'static_atr_threshold = float(os.getenv("ATR_MIN_PCT", "0.002"))'
    new_threshold = '''static_atr_threshold = (
                    float(os.getenv("EQUITY_ATR_MIN_PCT", "0.0005"))
                    if str(sym).endswith("@MISX")
                    else float(os.getenv("ATR_MIN_PCT", "0.002"))
                )'''

    if old_threshold not in text:
        raise SystemExit("PATCH_FAILED: static_atr_threshold block not found")

    text = text.replace(old_threshold, new_threshold, 1)

    old_audit_reason = "block_reason=vol_decision.reason,"
    new_audit_reason = '''block_reason=(
                            "equity_volatility_too_low"
                            if str(sym).endswith("@MISX") and str(vol_decision.reason) == "br_volatility_too_low"
                            else vol_decision.reason
                        ),'''

    if old_audit_reason not in text:
        raise SystemExit("PATCH_FAILED: vol_decision audit reason callsite not found")

    text = text.replace(old_audit_reason, new_audit_reason, 1)

    PATH.write_text(text, encoding="utf-8")

    print("EQUITY_VOLATILITY_GATE_SPLIT_PATCH_V1_OK")
    print("patched_file=src/finam_core/pipelines/paper_pipeline.py")
    print("equity_threshold_env=EQUITY_ATR_MIN_PCT")
    print("equity_threshold_default=0.0005")
    print("br_threshold_env=ATR_MIN_PCT")
    print("br_threshold_default=0.002")
    print("real_trading_enabled=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
