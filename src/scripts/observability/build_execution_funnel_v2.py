#!/usr/bin/env python3

import subprocess

def count(pattern: str) -> int:
    cmd = f'''
journalctl -u finam-paper-pipeline.service \
--since "30 minutes ago" \
--no-pager 2>/dev/null | grep -c "{pattern}" || true
'''
    result = subprocess.check_output(cmd, shell=True, text=True).strip()
    return int(result or 0)

generated = count("PIPE_SMART_ENTRY")
blocked = count("RUNTIME_GUARD_PRE_SIGNAL_BLOCK_SAVED")
edge = count("EDGE_REJECTED")
risk = count("RISK_REJECT")
execution = count("ORDER_REJECT")
filled = count("PIPE_FILLED")

blocked_for_funnel = min(blocked, generated)
excess_filter_blocks = max(0, blocked - generated)

after_filter = max(0, generated - blocked_for_funnel)
edge_for_funnel = min(edge, after_filter)
after_edge = max(0, after_filter - edge_for_funnel)
risk_for_funnel = min(risk, after_edge)
after_risk = max(0, after_edge - risk_for_funnel)

conv = 0.0
if generated > 0:
    conv = filled / generated * 100.0

print("=== EXECUTION FUNNEL V2 ===")
print(f"generated_signals={generated}")
print(f"filter_blocked={blocked_for_funnel}")
print(f"edge_rejected={edge_for_funnel}")
print(f"risk_rejected={risk_for_funnel}")
print(f"execution_rejected={execution}")
print(f"filled={filled}")
print()
print(f"after_filter={after_filter}")
print(f"after_edge={after_edge}")
print(f"after_risk={after_risk}")
print()

if excess_filter_blocks > 0:
    print(f"filter_blocked_raw={blocked}")
    print(f"filter_blocked_excess={excess_filter_blocks}")
    print("note=filter_blocks_exceed_generated_due_to_pre_signal_or_session_noise")
    print()

print(f"full_funnel_conversion={conv:.2f}%")
