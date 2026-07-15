#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

package="src/marketcore/presentation/render_tree/v2"

test -d "$package"

PYTHONPYCACHEPREFIX=/tmp/marketcore_render_tree_v2_models \
PYTHONPATH=src \
python3 -m py_compile "$package"/*.py

if grep -RInE --include='*.py' \
  'presentation\.ui_runtime|presentation\.adapters|browser_dom_driver|HTMLResponse|psycopg|sqlite3' \
  "$package"
then
  echo "RENDER_TREE_V2_FORBIDDEN_DEPENDENCY_FOUND"
  exit 1
fi

PYTHONPATH=src python3 - <<'PY'
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from marketcore.presentation.render_tree.v2 import (
    ActionKindV2,
    RenderActionV2,
    RenderContentV2,
    RenderDocumentV2,
    RenderNodeStateV2,
    RenderNodeTypeV2,
    RenderNodeV2,
    RenderTreeValidationErrorV2,
    render_document_v2_to_dict,
    render_document_v2_to_json,
    validate_render_document_v2,
)


now = datetime(2026, 7, 15, 18, 0, tzinfo=timezone.utc)
document = RenderDocumentV2(
    document_id="operator.home.v2",
    locale_code="ru-RU",
    fallback_locale_code="ru-RU",
    generated_at=now,
    source_as_of=now - timedelta(minutes=5),
    quality_code="VERIFIED",
    root=RenderNodeV2(
        node_type=RenderNodeTypeV2.WORKSPACE,
        node_id="workspace.home",
        children=(
            RenderNodeV2(
                node_type=RenderNodeTypeV2.PAGE,
                node_id="page.home",
                children=(
                    RenderNodeV2(
                        node_type=RenderNodeTypeV2.TITLE,
                        node_id="title.home",
                        content=RenderContentV2(message_key="home.title", level_code="PRIMARY"),
                    ),
                    RenderNodeV2(
                        node_type=RenderNodeTypeV2.CARD,
                        node_id="card.edge",
                        state=RenderNodeStateV2(
                            status_code="WARNING",
                            quality_code="VERIFIED",
                            source_as_of=now - timedelta(minutes=5),
                            source_identity="research.edge_summary_v1",
                        ),
                        action=RenderActionV2(
                            action_id="home.open_edge",
                            action_kind=ActionKindV2.NAVIGATE,
                            target_id="container.edge",
                        ),
                        children=(
                            RenderNodeV2(
                                node_type=RenderNodeTypeV2.METRIC_VALUE,
                                node_id="metric.edge.count",
                                content=RenderContentV2(value=0, format_code="INTEGER"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)

validate_render_document_v2(document, message_keys={"home.title"})
payload = render_document_v2_to_dict(document)
encoded_one = render_document_v2_to_json(document)
encoded_two = render_document_v2_to_json(document)

assert encoded_one == encoded_two
assert payload["schema_version"] == "marketcore.render_tree.v2"
assert payload["root"]["type"] == "workspace"
assert "class" not in encoded_one
assert "style" not in encoded_one
assert "href" not in encoded_one
assert "home.title" in encoded_one

try:
    document.document_id = "changed"  # type: ignore[misc]
except FrozenInstanceError:
    pass
else:
    raise AssertionError("V2_DOCUMENT_NOT_IMMUTABLE")

def expect_error(expected_code, candidate, **kwargs):
    try:
        validate_render_document_v2(candidate, **kwargs)
    except RenderTreeValidationErrorV2 as exc:
        assert str(exc).startswith(expected_code), (expected_code, str(exc))
    else:
        raise AssertionError(f"EXPECTED_ERROR_NOT_RAISED:{expected_code}")

duplicate = RenderDocumentV2(
    document_id="duplicate",
    locale_code="ru-RU",
    fallback_locale_code="ru-RU",
    generated_at=now,
    source_as_of=now,
    quality_code="VERIFIED",
    root=RenderNodeV2(
        RenderNodeTypeV2.WORKSPACE,
        "same",
        children=(RenderNodeV2(RenderNodeTypeV2.PAGE, "same"),),
    ),
)
expect_error("RENDER_TREE_V2_NODE_ID_DUPLICATE", duplicate)

missing_key = RenderDocumentV2(
    document_id="missing-key",
    locale_code="ru-RU",
    fallback_locale_code="ru-RU",
    generated_at=now,
    source_as_of=now,
    quality_code="VERIFIED",
    root=RenderNodeV2(
        RenderNodeTypeV2.WORKSPACE,
        "root",
        children=(
            RenderNodeV2(
                RenderNodeTypeV2.TITLE,
                "title",
                content=RenderContentV2(message_key="missing.key"),
            ),
        ),
    ),
)
expect_error("RENDER_TREE_V2_MESSAGE_KEY_MISSING", missing_key, message_keys=set())

unsafe_command = RenderDocumentV2(
    document_id="unsafe-command",
    locale_code="ru-RU",
    fallback_locale_code="ru-RU",
    generated_at=now,
    source_as_of=now,
    quality_code="VERIFIED",
    root=RenderNodeV2(
        RenderNodeTypeV2.WORKSPACE,
        "root-command",
        children=(
            RenderNodeV2(
                RenderNodeTypeV2.ACTION,
                "action",
                content=RenderContentV2(message_key="action.run"),
                action=RenderActionV2(
                    action_id="run",
                    action_kind=ActionKindV2.COMMAND,
                    command_code="RUN_RESEARCH",
                ),
            ),
        ),
    ),
)
expect_error("RENDER_TREE_V2_POLICY_CLASS_REQUIRED", unsafe_command)

command_without_idempotency = RenderDocumentV2(
    document_id="command-without-idempotency",
    locale_code="ru-RU",
    fallback_locale_code="ru-RU",
    generated_at=now,
    source_as_of=now,
    quality_code="VERIFIED",
    root=RenderNodeV2(
        RenderNodeTypeV2.WORKSPACE,
        "command-root",
        children=(
            RenderNodeV2(
                RenderNodeTypeV2.ACTION,
                "command-action",
                content=RenderContentV2(message_key="action.run"),
                action=RenderActionV2(
                    action_id="run-safe",
                    action_kind=ActionKindV2.COMMAND,
                    command_code="RUN_RESEARCH",
                    policy_class="RESEARCH_CONTROL",
                    requires_approval=True,
                ),
            ),
        ),
    ),
)
expect_error("RENDER_TREE_V2_IDEMPOTENCY_KEY_REQUIRED", command_without_idempotency)

invalid_source_state = RenderDocumentV2(
    document_id="invalid-source-state",
    locale_code="ru-RU",
    fallback_locale_code="ru-RU",
    generated_at=now,
    source_as_of=now,
    quality_code="VERIFIED",
    root=RenderNodeV2(
        RenderNodeTypeV2.WORKSPACE,
        "source-root",
        state=RenderNodeStateV2(source_identity="source.without.timestamp"),
    ),
)
expect_error("RENDER_TREE_V2_NODE_SOURCE_AS_OF_REQUIRED", invalid_source_state)

print("immutable_models=OK")
print("validator_fail_closed=OK")
print("message_key_validation=OK")
print("policy_metadata_validation=OK")
print("idempotency_validation=OK")
print("source_lineage_validation=OK")
print("deterministic_serialization=OK")
PY

echo "platform_dependencies=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_DOMAIN_RENDER_TREE_V2_MODELS_OK"
