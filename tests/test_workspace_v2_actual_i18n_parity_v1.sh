#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

echo "=== TEST WORKSPACE V2 ACTUAL I18N PARITY V1 ==="

PYTHONPATH=src "$PY" - <<'PY'
import json
import urllib.request

BASE = "http://127.0.0.1:8080"


def get_json(path: str):
    with urllib.request.urlopen(
        BASE + path,
        timeout=20,
    ) as response:
        if response.status != 200:
            raise RuntimeError(
                f"HTTP_STATUS_INVALID:{path}:{response.status}"
            )

        print(
            "HTTP_ROW "
            f"path={path} "
            f"status={response.status} "
            f"content_type="
            f"{response.headers.get('Content-Type')}"
        )

        return json.load(response)


tree = get_json(
    "/api/v2/domain-render-tree/research"
)

catalog = get_json(
    "/api/v2/i18n/catalog"
)

messages = catalog.get("messages")

if not isinstance(messages, dict):
    raise RuntimeError(
        "I18N_CATALOG_MESSAGES_INVALID"
    )

used = {}


def add_key(key, source, node_id):
    if not isinstance(key, str):
        return

    key = key.strip()

    if not key:
        return

    used.setdefault(
        key,
        [],
    ).append(
        (source, node_id)
    )


def walk(value):
    if isinstance(value, dict):
        node_id = str(
            value.get("node_id") or ""
        )

        content = value.get("content")

        if isinstance(content, dict):
            add_key(
                content.get("message_key"),
                "message_key",
                node_id,
            )

            args = content.get(
                "message_args"
            )

            if isinstance(args, dict):
                for name, item in args.items():
                    if (
                        isinstance(name, str)
                        and name.endswith("_key")
                    ):
                        add_key(
                            item,
                            f"message_args.{name}",
                            node_id,
                        )

        for child in value.values():
            walk(child)

    elif isinstance(value, list):
        for child in value:
            walk(child)


walk(tree)

missing = sorted(
    key
    for key in used
    if key not in messages
)

print()
print(
    "ACTUAL_I18N_PARITY_SUMMARY "
    f"render_message_keys={len(used)} "
    f"catalog_messages={len(messages)} "
    f"missing_message_keys={len(missing)}"
)

for key in missing:
    for source, node_id in used[key]:
        print(
            "MISSING_MESSAGE "
            f"key={key} "
            f"source={source} "
            f"node_id={node_id}"
        )

if missing:
    print(
        "VERDICT="
        "WORKSPACE_V2_ACTUAL_I18N_PARITY_FAILED"
    )
    raise SystemExit(1)

print("actual_render_tree_used=1")
print("actual_i18n_catalog_used=1")
print("message_key_checked=1")
print("message_args_dynamic_keys_checked=1")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "WORKSPACE_V2_ACTUAL_I18N_PARITY_OK"
)
PY

echo
echo "VERDICT=TEST_WORKSPACE_V2_ACTUAL_I18N_PARITY_V1_OK"
