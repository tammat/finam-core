from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from marketcore.presentation.render_tree.node_types import RenderNodeType


class UiRuntimeContractValidationErrorV1(ValueError):
    """Ошибка проверки payload по контракту UI Runtime V1."""


@dataclass(frozen=True, slots=True)
class UiRuntimeNodeRuleV1:
    node_type: RenderNodeType
    allowed_props: frozenset[str]
    required_props: frozenset[str] = frozenset()
    allows_text: bool = False
    allows_children: bool = False


@dataclass(frozen=True, slots=True)
class UiRuntimeContractV1:
    contract_version: str
    render_tree_schema_version: str
    root_node_type: RenderNodeType
    supported_node_types: frozenset[RenderNodeType]
    node_rules: dict[RenderNodeType, UiRuntimeNodeRuleV1]
    allowed_theme_codes: frozenset[str]
    navigation_schemes: frozenset[str]
    maximum_tree_depth: int
    maximum_nodes: int


_COMMON_CONTAINER_PROPS = frozenset(
    {
        "class",
        "style",
        "role",
        "aria_label",
        "id",
        "data-section",
        "data-card",
        "data-status",
        "data-field",
    }
)

_TEXT_PROPS = frozenset(
    {
        "class",
        "style",
        "role",
        "aria_label",
        "data-field",
    }
)

_NODE_RULES: dict[RenderNodeType, UiRuntimeNodeRuleV1] = {
    RenderNodeType.WORKSPACE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.WORKSPACE,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.PAGE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.PAGE,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.HEADER: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.HEADER,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
        allows_children=True,
    ),
    RenderNodeType.SECTION: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.SECTION,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.GRID: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.GRID,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.CARD: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.CARD,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.TABLE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TABLE,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.TABLE_HEAD: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TABLE_HEAD,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.TABLE_BODY: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TABLE_BODY,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.TABLE_ROW: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TABLE_ROW,
        allowed_props=_COMMON_CONTAINER_PROPS | frozenset({"activation_target", "tab_index"}),
        allows_children=True,
    ),
    RenderNodeType.TABLE_HEADER_CELL: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TABLE_HEADER_CELL,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
    ),
    RenderNodeType.TABLE_CELL: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TABLE_CELL,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
    ),
    RenderNodeType.TITLE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TITLE,
        allowed_props=_TEXT_PROPS | frozenset({"level"}),
        required_props=frozenset({"level"}),
        allows_text=True,
    ),
    RenderNodeType.SUBTITLE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.SUBTITLE,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
    ),
    RenderNodeType.TEXT: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.TEXT,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
    ),
    RenderNodeType.METRIC_LIST: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.METRIC_LIST,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.METRIC_ROW: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.METRIC_ROW,
        allowed_props=_COMMON_CONTAINER_PROPS,
        allows_children=True,
    ),
    RenderNodeType.METRIC_LABEL: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.METRIC_LABEL,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
    ),
    RenderNodeType.METRIC_VALUE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.METRIC_VALUE,
        allowed_props=_TEXT_PROPS,
        allows_text=True,
    ),
    RenderNodeType.ACTION: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.ACTION,
        allowed_props=frozenset(
            {
                "class",
                "style",
                "role",
                "aria_label",
                "href",
                "action_code",
                "target",
                "disabled",
            }
        ),
        allows_text=True,
    ),
    RenderNodeType.BADGE: UiRuntimeNodeRuleV1(
        node_type=RenderNodeType.BADGE,
        allowed_props=_TEXT_PROPS | frozenset({"status"}),
        allows_text=True,
    ),
}


MARKETCORE_UI_RUNTIME_CONTRACT_V1 = UiRuntimeContractV1(
    contract_version="marketcore.ui_runtime.contract.v1",
    render_tree_schema_version="marketcore.render_tree.v1",
    root_node_type=RenderNodeType.WORKSPACE,
    supported_node_types=frozenset(_NODE_RULES),
    node_rules=_NODE_RULES,
    allowed_theme_codes=frozenset(
        {
            "DEFAULT",
            "PHONE",
        }
    ),
    navigation_schemes=frozenset(
        {
            "/",
            "http://",
            "https://",
        }
    ),
    maximum_tree_depth=32,
    maximum_nodes=10_000,
)


def validate_ui_runtime_payload_v1(
    payload: dict[str, Any],
    *,
    contract: UiRuntimeContractV1 = MARKETCORE_UI_RUNTIME_CONTRACT_V1,
) -> None:
    if not isinstance(payload, dict):
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_PAYLOAD_MUST_BE_OBJECT"
        )

    schema_version = payload.get("schema_version")

    if schema_version != contract.render_tree_schema_version:
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_SCHEMA_VERSION_UNSUPPORTED:"
            f"{schema_version}"
        )

    root = payload.get("root")

    if not isinstance(root, dict):
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_ROOT_MUST_BE_OBJECT"
        )

    state = {
        "nodes": 0,
    }

    _validate_node_v1(
        root,
        contract=contract,
        depth=1,
        state=state,
    )

    if root.get("type") != contract.root_node_type.value:
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_ROOT_TYPE_INVALID:"
            f"{root.get('type')}"
        )


def _validate_node_v1(
    node: dict[str, Any],
    *,
    contract: UiRuntimeContractV1,
    depth: int,
    state: dict[str, int],
) -> None:
    if depth > contract.maximum_tree_depth:
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_MAXIMUM_TREE_DEPTH_EXCEEDED"
        )

    state["nodes"] += 1

    if state["nodes"] > contract.maximum_nodes:
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_MAXIMUM_NODE_COUNT_EXCEEDED"
        )

    node_type_raw = node.get("type")

    try:
        node_type = RenderNodeType(node_type_raw)
    except (TypeError, ValueError) as exc:
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_TYPE_UNSUPPORTED:{node_type_raw}"
        ) from exc

    rule = contract.node_rules.get(node_type)

    if rule is None:
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_RULE_NOT_FOUND:{node_type.value}"
        )

    props = node.get("props", {})

    if not isinstance(props, dict):
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_PROPS_MUST_BE_OBJECT:{node_type.value}"
        )

    unknown_props = set(props) - set(rule.allowed_props)

    if unknown_props:
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_NODE_PROP_UNSUPPORTED:"
            f"{node_type.value}:"
            f"{','.join(sorted(unknown_props))}"
        )

    missing_props = set(rule.required_props) - set(props)

    if missing_props:
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_NODE_PROP_REQUIRED:"
            f"{node_type.value}:"
            f"{','.join(sorted(missing_props))}"
        )

    text = node.get("text", "")

    if not isinstance(text, str):
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_TEXT_MUST_BE_STRING:{node_type.value}"
        )

    if text and not rule.allows_text:
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_TEXT_NOT_ALLOWED:{node_type.value}"
        )

    children = node.get("children", [])

    if not isinstance(children, list):
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_CHILDREN_MUST_BE_ARRAY:{node_type.value}"
        )

    if children and not rule.allows_children:
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_NODE_CHILDREN_NOT_ALLOWED:{node_type.value}"
        )

    if node_type == RenderNodeType.TITLE:
        _validate_title_v1(props)

    if node_type == RenderNodeType.ACTION:
        _validate_action_v1(
            props,
            contract=contract,
        )

    for child in children:
        if not isinstance(child, dict):
            raise UiRuntimeContractValidationErrorV1(
                f"UI_RUNTIME_CHILD_MUST_BE_OBJECT:{node_type.value}"
            )

        _validate_node_v1(
            child,
            contract=contract,
            depth=depth + 1,
            state=state,
        )


def _validate_title_v1(props: dict[str, Any]) -> None:
    level = props.get("level")

    if level not in (1, 2, 3):
        raise UiRuntimeContractValidationErrorV1(
            f"UI_RUNTIME_TITLE_LEVEL_INVALID:{level}"
        )


def _validate_action_v1(
    props: dict[str, Any],
    *,
    contract: UiRuntimeContractV1,
) -> None:
    target = props.get("target")
    href = props.get("href")

    navigation_target = target if target is not None else href

    if navigation_target is None:
        return

    if not isinstance(navigation_target, str):
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_ACTION_TARGET_MUST_BE_STRING"
        )

    if not navigation_target.startswith(
        tuple(contract.navigation_schemes)
    ):
        raise UiRuntimeContractValidationErrorV1(
            "UI_RUNTIME_ACTION_TARGET_SCHEME_FORBIDDEN:"
            f"{navigation_target}"
        )
