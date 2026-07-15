from __future__ import annotations

from marketcore.presentation.navigation.container_registry_v2 import resolve_container_v2
from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderActionV2, RenderDocumentV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


class RuntimeNavigationErrorV2(ValueError):
    pass


def build_container_navigation_action_v2(container_id: str) -> RenderActionV2:
    definition = resolve_container_v2(container_id)
    if not definition.target_ready:
        raise RuntimeNavigationErrorV2(f"NAVIGATION_TARGET_NOT_READY:{container_id}")
    return RenderActionV2(
        action_id=f"navigation.open.{definition.container_code.value.lower()}",
        action_kind=ActionKindV2.NAVIGATE,
        target_id=definition.container_id,
    )


def open_container_navigation_target_v2(
    action: RenderActionV2,
    *,
    timezone_code: str | None = None,
) -> RenderDocumentV2:
    if action.action_kind is not ActionKindV2.NAVIGATE or not action.enabled:
        raise RuntimeNavigationErrorV2(f"NAVIGATION_ACTION_NOT_ALLOWED:{action.action_id}")
    if action.target_id is None:
        raise RuntimeNavigationErrorV2(f"NAVIGATION_TARGET_REQUIRED:{action.action_id}")
    definition = resolve_container_v2(action.target_id)
    if definition.producer_code is None:
        raise RuntimeNavigationErrorV2(f"NAVIGATION_TARGET_NOT_READY:{action.target_id}")
    return build_domain_document_v2(definition.producer_code, timezone_code=timezone_code)
