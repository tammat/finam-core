#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

TEST="$ROOT/scripts/test_multi_asset_breakout_telegram_systemd_runtime_validation_v1.sh"
VALIDATOR="$ROOT/src/scripts/research/build_multi_asset_breakout_telegram_systemd_runtime_validation_v1.py"
UNIT="$ROOT/deploy/systemd/finam-multi-asset-breakout-telegram.service"

echo "=== AUDIT TELEGRAM MULTI ASSET RUNTIME ACTIONS V1 ==="

for file in "$TEST" "$VALIDATOR" "$UNIT"; do
    [[ -f "$file" ]] || {
        echo "ERROR=file_missing:$file"
        exit 1
    }
done

bash -n "$TEST"

"$PYTHON" -m py_compile "$VALIDATOR"

"$PYTHON" - "$TEST" "$VALIDATOR" "$UNIT" <<'PY'
from __future__ import annotations

import ast
import pathlib
import re
import sys


test_path = pathlib.Path(sys.argv[1])
validator_path = pathlib.Path(sys.argv[2])
unit_path = pathlib.Path(sys.argv[3])

test_source = test_path.read_text(encoding="utf-8")
validator_source = validator_path.read_text(encoding="utf-8")
unit_source = unit_path.read_text(encoding="utf-8")

validator_tree = ast.parse(
    validator_source,
    filename=str(validator_path),
)

combined = "\n".join(
    (
        test_source,
        validator_source,
        unit_source,
    )
)

markers = {
    "systemctl": r"\bsystemctl\b",
    "sudo": r"\bsudo\b",
    "curl": r"\bcurl\b",
    "telegram_api": r"api\.telegram\.org",
    "send_message": r"sendMessage",
    "requests_post": r"requests\.post",
    "service_restart": r"\brestart\b",
    "service_start": r"\bstart\b",
    "service_stop": r"\bstop\b",
    "service_enable": r"\benable\b",
    "service_disable": r"\bdisable\b",
    "kill": r"\bkill\b|\bpkill\b",
}

for name, pattern in markers.items():
    count = len(
        re.findall(
            pattern,
            combined,
            flags=re.IGNORECASE,
        )
    )
    print(f"action_marker={name} count={count}")

python_calls: list[str] = []

for node in ast.walk(validator_tree):
    if not isinstance(node, ast.Call):
        continue

    if isinstance(node.func, ast.Name):
        python_calls.append(node.func.id)
    elif isinstance(node.func, ast.Attribute):
        python_calls.append(node.func.attr)

for name in (
    "run",
    "Popen",
    "system",
    "remove",
    "unlink",
    "execute",
    "commit",
    "post",
):
    print(
        f"validator_call={name} "
        f"count={python_calls.count(name)}"
    )

real_send_guards = (
    "telegram_dry_run",
    "telegram_real_send",
    "TELEGRAM_DRY_RUN",
)

guard_count = sum(
    combined.count(marker)
    for marker in real_send_guards
)

print(f"telegram_send_guard_count={guard_count}")

if guard_count == 0:
    raise SystemExit(
        "ERROR=telegram_send_guard_missing"
    )

dangerous_shell_patterns = (
    r"systemctl\s+(restart|start|stop|enable|disable)",
    r"sudo\s+systemctl",
    r"curl.+api\.telegram\.org",
)

dangerous_matches: list[str] = []

for pattern in dangerous_shell_patterns:
    for match in re.finditer(
        pattern,
        test_source,
        flags=re.IGNORECASE,
    ):
        dangerous_matches.append(match.group(0))

print(f"dangerous_runtime_action_count={len(dangerous_matches)}")

for match in dangerous_matches:
    print(f"DANGEROUS_ACTION value={match}")

if dangerous_matches:
    print("classification=RUNTIME_MUTATING_TEST")
    print("runtime_test_allowed=0")
else:
    print("classification=READ_ONLY_RUNTIME_VALIDATION")
    print("runtime_test_allowed=1")

print("writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TELEGRAM_MULTI_ASSET_RUNTIME_ACTIONS_V1_READY")
PY
