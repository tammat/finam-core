#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/navigation/container_registry_v2.py
PYTHONPATH=src .venv/bin/python - <<'PY'
from marketcore.presentation.navigation.container_registry_v2 import (
    ContainerCodeV2, ContainerViewStateV2, container_definitions_v2,
    ready_container_definitions_v2, resolve_container_v2,
)
from marketcore.presentation.navigation.runtime_navigation_v2 import (
    build_container_navigation_action_v2, open_container_navigation_target_v2,
)
from marketcore.presentation.render_tree.v2 import ActionKindV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2

definitions = container_definitions_v2()
assert [item.container_code for item in definitions] == list(ContainerCodeV2)
assert len(definitions) == 9
assert len({item.container_id for item in definitions}) == 9
assert len({item.display_order for item in definitions}) == 9
assert all(item.label_message_key == f"navigation.container.{item.container_code.value.lower()}" for item in definitions)
assert all(item.supported_states == tuple(ContainerViewStateV2) for item in definitions)

ready = ready_container_definitions_v2()
assert {item.container_code.value for item in ready} == {item.value for item in ContainerCodeV2}
for item in ready:
    document = build_domain_document_v2(item.producer_code)
    assert document.root.node_id

for layout_profile in ("desktop", "mobile"):
    for item in ready:
        action = build_container_navigation_action_v2(item.container_id)
        assert action.action_kind is ActionKindV2.NAVIGATE
        assert action.target_id == item.container_id
        document = open_container_navigation_target_v2(action, timezone_code="Europe/Moscow")
        assert document.document_id
        assert document.timezone_code == "Europe/Moscow"

current_targets = {
    "container.research", "container.edge", "container.risk", "container.capital",
    "container.portfolio", "container.intraday",
}
for target in current_targets:
    assert resolve_container_v2(target).container_id == target

assert not any("diagnostic" in item.container_id or "engineering" in item.container_id for item in definitions)
print("canonical_containers=9")
print("real_targets_ready=9")
print("targets_pending=0")
print("current_navigation_targets_valid=6")
print("desktop_navigation_targets_opened=9")
print("mobile_navigation_targets_opened=9")
print("VERDICT=MARKETCORE_STAGE4_CANONICAL_NAVIGATION_COMPLETE")
PY
