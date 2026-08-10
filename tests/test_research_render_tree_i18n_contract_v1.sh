#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

"$PY" - <<'PY'
import json
import re
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8080"

def fetch(path, media):
    req = Request(
        BASE + path,
        headers={"Accept": media},
    )
    with urlopen(req, timeout=30) as response:
        content_type = response.headers.get(
            "Content-Type", ""
        )
        if response.status != 200:
            raise SystemExit(
                f"ERROR=HTTP_STATUS:{response.status}:{path}"
            )
        if not content_type.lower().startswith(
            media.lower()
        ):
            raise SystemExit(
                f"ERROR=CONTENT_TYPE:{content_type}:{path}"
            )
        return json.load(response)

catalog = fetch(
    "/api/v2/i18n/catalog?locale=ru-RU",
    "application/vnd.marketcore.i18n-catalog+json",
)

document = fetch(
    "/api/v2/domain-render-tree/research",
    "application/vnd.marketcore.render-tree+json",
)

messages = catalog.get("messages") or {}
missing = []
argument_failures = []

def validate_key(node_id, key, args, source):
    if not key:
        return

    template = messages.get(key)

    if not isinstance(template, str) or not template:
        missing.append((node_id, key, source))
        return

    required = set(
        re.findall(
            r"\{([A-Za-z0-9_]+)\}",
            template,
        )
    )

    absent = sorted(required - set(args))

    if absent:
        argument_failures.append(
            (node_id, key, source, absent)
        )

def walk(node):
    content = node.get("content")

    if isinstance(content, dict):
        key = content.get("message_key")
        args = content.get("message_args") or {}

        validate_key(
            node.get("node_id"),
            key,
            args,
            "message_key",
        )

        validate_key(
            node.get("node_id"),
            args.get("tooltip_key"),
            {},
            "tooltip_key",
        )

    for child in node.get("children") or []:
        walk(child)

walk(document["root"])

for node_id, key, source in missing:
    print(
        f"missing_message node_id={node_id} "
        f"source={source} key={key}"
    )

for node_id, key, source, absent in argument_failures:
    print(
        f"missing_argument node_id={node_id} "
        f"source={source} key={key} "
        f"args={','.join(absent)}"
    )

print(f"missing_message_keys={len(missing)}")
print(
    "message_argument_failures="
    f"{len(argument_failures)}"
)

if missing or argument_failures:
    raise SystemExit(1)

print("research_i18n_contract=1")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RESEARCH_RENDER_TREE_I18N_CONTRACT_V1_OK"
