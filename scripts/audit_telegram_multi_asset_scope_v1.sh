#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

FILES=(
  "deploy/systemd/finam-multi-asset-breakout-telegram.service"
  "scripts/test_multi_asset_breakout_telegram_systemd_plan_v1.sh"
  "scripts/test_multi_asset_breakout_telegram_systemd_runtime_validation_v1.sh"
  "scripts/test_telegram_signal_dispatcher.sh"
  "src/finam_core/notifications/telegram_signal_dispatcher.py"
  "src/scripts/research/build_multi_asset_breakout_telegram_systemd_runtime_validation_v1.py"
)

echo "=== AUDIT TELEGRAM MULTI ASSET SCOPE V1 ==="

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=file_missing:$file"
        exit 1
    }

    echo "file=$file"
done

echo
echo "=== 1. GIT DIFF ==="

git diff --stat -- "${FILES[@]}"
git diff --check -- "${FILES[@]}"

echo
echo "=== 2. PYTHON COMPILE ==="

"$PYTHON" -m py_compile \
  src/finam_core/notifications/telegram_signal_dispatcher.py \
  src/scripts/research/build_multi_asset_breakout_telegram_systemd_runtime_validation_v1.py

echo "python_compile=OK"

echo
echo "=== 3. BASH SYNTAX ==="

for file in \
  scripts/test_multi_asset_breakout_telegram_systemd_plan_v1.sh \
  scripts/test_multi_asset_breakout_telegram_systemd_runtime_validation_v1.sh \
  scripts/test_telegram_signal_dispatcher.sh
do
    bash -n "$file"
    echo "bash_syntax=OK file=$file"
done

echo
echo "=== 4. SYSTEMD UNIT SYNTAX ==="

if command -v systemd-analyze >/dev/null 2>&1; then
    systemd-analyze verify \
      deploy/systemd/finam-multi-asset-breakout-telegram.service \
      >/tmp/telegram_multi_asset_systemd_verify_v1.log 2>&1 || {
        cat /tmp/telegram_multi_asset_systemd_verify_v1.log
        echo "ERROR=systemd_unit_verify_failed"
        exit 1
    }

    echo "systemd_unit_verify=OK"
else
    echo "systemd_unit_verify=SKIPPED"
fi

echo
echo "=== 5. SOURCE CONTRACT ==="

"$PYTHON" - <<'PY'
from __future__ import annotations

import ast
import pathlib
import re


root = pathlib.Path("/opt/finam-core")

dispatcher_path = (
    root
    / "src/finam_core/notifications/telegram_signal_dispatcher.py"
)
runtime_validator_path = (
    root
    / "src/scripts/research/"
    "build_multi_asset_breakout_telegram_systemd_runtime_validation_v1.py"
)
unit_path = (
    root
    / "deploy/systemd/"
    "finam-multi-asset-breakout-telegram.service"
)

dispatcher_source = dispatcher_path.read_text(encoding="utf-8")
validator_source = runtime_validator_path.read_text(encoding="utf-8")
unit_source = unit_path.read_text(encoding="utf-8")

dispatcher_tree = ast.parse(
    dispatcher_source,
    filename=str(dispatcher_path),
)
validator_tree = ast.parse(
    validator_source,
    filename=str(runtime_validator_path),
)

forbidden_dispatcher_markers = (
    "sqlite3",
    "subprocess.run",
    "os.system",
    "systemctl",
)

for marker in forbidden_dispatcher_markers:
    count = dispatcher_source.count(marker)
    print(f"dispatcher_forbidden_marker={marker} count={count}")

    if count:
        raise SystemExit(
            f"ERROR=dispatcher_forbidden_marker:{marker}"
        )

functions = {
    node.name
    for node in ast.walk(dispatcher_tree)
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef),
    )
}

classes = {
    node.name
    for node in ast.walk(dispatcher_tree)
    if isinstance(node, ast.ClassDef)
}

print(
    "dispatcher_function_count="
    + str(len(functions))
)
print(
    "dispatcher_class_count="
    + str(len(classes))
)

http_markers = (
    "urlopen",
    "requests.",
    "httpx.",
    "aiohttp",
)

http_client_count = sum(
    dispatcher_source.count(marker)
    for marker in http_markers
)

print(f"telegram_http_client_markers={http_client_count}")

if http_client_count == 0:
    raise SystemExit(
        "ERROR=telegram_http_client_not_found"
    )

token_markers = (
    "TELEGRAM_BOT_TOKEN",
    "bot_token",
    "telegram_token",
)

token_reference_count = sum(
    dispatcher_source.count(marker)
    + unit_source.count(marker)
    for marker in token_markers
)

print(f"telegram_token_reference_count={token_reference_count}")

if token_reference_count == 0:
    raise SystemExit(
        "ERROR=telegram_token_reference_missing"
    )

secret_literal_patterns = (
    r"\b\d{8,12}:[A-Za-z0-9_-]{20,}\b",
    r"https://api\.telegram\.org/bot\d+:[A-Za-z0-9_-]+",
)

for pattern in secret_literal_patterns:
    matches = re.findall(
        pattern,
        dispatcher_source + "\n" + unit_source,
    )

    print(
        "embedded_secret_match_count="
        + str(len(matches))
    )

    if matches:
        raise SystemExit(
            "ERROR=embedded_telegram_secret"
        )

required_unit_markers = (
    "[Unit]",
    "[Service]",
    "ExecStart=",
)

for marker in required_unit_markers:
    count = unit_source.count(marker)
    print(f"unit_required_marker={marker} count={count}")

    if count != 1:
        raise SystemExit(
            f"ERROR=unit_required_marker:{marker}:{count}"
        )


def unit_directive(name: str) -> str | None:
    prefix = name + "="

    for raw_line in unit_source.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith(prefix):
            return line[len(prefix):].strip()

    return None


service_type = unit_directive("Type") or "simple"
restart_policy = unit_directive("Restart")

print(f"unit_service_type={service_type}")
print(
    "unit_restart_policy="
    + (restart_policy if restart_policy is not None else "ABSENT")
)

if service_type == "oneshot":
    # Для oneshot отсутствие Restart является допустимым.
    restart_contract = (
        "ONESHOT_RESTART_OPTIONAL"
        if restart_policy is None
        else "ONESHOT_RESTART_PRESENT"
    )
else:
    # Долгоживущий Telegram worker должен восстанавливаться
    # после аварийного завершения.
    if restart_policy not in {
        "always",
        "on-failure",
        "on-abnormal",
        "on-abort",
        "on-watchdog",
    }:
        raise SystemExit(
            "ERROR=long_running_restart_policy:"
            + str(restart_policy)
        )

    restart_contract = "LONG_RUNNING_RESTART_REQUIRED"

print(f"unit_restart_contract={restart_contract}")

write_calls = 0

for node in ast.walk(dispatcher_tree):
    if not isinstance(node, ast.Call):
        continue

    name = ""

    if isinstance(node.func, ast.Name):
        name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        name = node.func.attr

    if name in {
        "execute",
        "executemany",
        "commit",
        "delete",
        "unlink",
        "remove",
    }:
        write_calls += 1

print(f"dispatcher_potential_write_calls={write_calls}")
print("source_contract=OK")
PY

echo
echo "=== 6. DIFF SAFETY MARKERS ==="

DIFF_FILE="/tmp/telegram_multi_asset_diff_v1.patch"

git diff -- "${FILES[@]}" > "$DIFF_FILE"

for marker in \
  'sqlite3' \
  'DROP TABLE' \
  'TRUNCATE ' \
  'DELETE FROM' \
  'execution_enabled=1' \
  'micro_live_allowed=1'
do
    count="$(
        grep -cF "$marker" "$DIFF_FILE" || true
    )"

    echo "diff_forbidden_marker=$marker count=$count"

    [[ "$count" -eq 0 ]]
done

echo
echo "changed_files=${#FILES[@]}"
echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TELEGRAM_MULTI_ASSET_SCOPE_V1_READY"
