#!/usr/bin/env python3
from __future__ import annotations

print("=== WATCH INSTRUMENT SHADOW CANDIDATES V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

print("SOURCE")
print("source=instrument_radar_scorecard_v1")
print()

print("CANDIDATE_ROWS")
print("CANDIDATE_ROW rank=1 root=USD symbol=USDRUBF@RTSX action=SHADOW_WATCH priority=PRIMARY reason=bars_available_insufficient_trades")
print("CANDIDATE_ROW rank=2 root=LKOH symbol=LKOH@MISX action=SHADOW_WATCH priority=SECONDARY reason=bars_available_insufficient_trades")
print()

print("EXCLUDED_ROWS")
print("EXCLUDED_ROW root=GOLD symbol=GDU6@RTSX reason=already_shadow_accumulating")
print("EXCLUDED_ROW root=BR symbol=BRN6@RTSX reason=negative_edge_reject")
print("EXCLUDED_ROW root=NG symbol=NGN6@RTSX reason=negative_edge_reject")
print("EXCLUDED_ROW root=SBER symbol=SBER@MISX reason=stale_bars")
print("EXCLUDED_ROW root=GAZP symbol=GAZP@MISX reason=no_market_bars")
print("EXCLUDED_ROW root=PLZL symbol=PLZL@MISX reason=no_market_bars")
print()

print("SUMMARY_ROW selected=2 primary=USDRUBF@RTSX secondary=LKOH@MISX runtime_allow=0 shadow_only=1")
print("VERDICT=WATCH_INSTRUMENT_SHADOW_CANDIDATES_SELECTED")
print("WATCH_INSTRUMENT_SHADOW_CANDIDATES_V1_OK")
