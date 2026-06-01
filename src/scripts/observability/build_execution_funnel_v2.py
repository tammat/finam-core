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

after_filter = generated - blocked
after_edge = after_filter - edge
after_risk = after_edge - risk

conv = 0.0
if generated > 0:
    conv = filled / generated * 100.0

print("=== EXECUTION FUNNEL V2 ===")
print(f"generated_signals={generated}")
print(f"filter_blocked={blocked}")
print(f"edge_rejected={edge}")
print(f"risk_rejected={risk}")
print(f"execution_rejected={execution}")
print(f"filled={filled}")
print()
print(f"after_filter={after_filter}")
print(f"after_edge={after_edge}")
print(f"after_risk={after_risk}")
print()
print(f"full_funnel_conversion={conv:.2f}%")
