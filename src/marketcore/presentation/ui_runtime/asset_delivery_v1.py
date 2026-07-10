from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class UiRuntimeAssetDeliveryErrorV1(RuntimeError):
    """Ошибка доставки статического ресурса UI Runtime V1."""


@dataclass(frozen=True, slots=True)
class UiRuntimeAssetDefinitionV1:
    asset_code: str
    route: str
    relative_path: str
    content_type: str


@dataclass(frozen=True, slots=True)
class UiRuntimeAssetResponseV1:
    status_code: int
    content_type: str
    body: bytes


_ASSET_ROOT = Path(__file__).resolve().parent / "assets" / "v1"

UI_RUNTIME_ASSETS_V1: tuple[UiRuntimeAssetDefinitionV1, ...] = (
    UiRuntimeAssetDefinitionV1(
        asset_code="runtime_js",
        route="/assets/marketcore/ui-runtime/v1/runtime.js",
        relative_path="runtime_v1.js",
        content_type="application/javascript; charset=utf-8",
    ),
    UiRuntimeAssetDefinitionV1(
        asset_code="runtime_css",
        route="/assets/marketcore/ui-runtime/v1/runtime.css",
        relative_path="runtime_v1.css",
        content_type="text/css; charset=utf-8",
    ),
    UiRuntimeAssetDefinitionV1(
        asset_code="render_tree_validator_js",
        route="/assets/marketcore/ui-runtime/v1/render-tree-validator.js",
        relative_path="render_tree_validator_v1.js",
        content_type="application/javascript; charset=utf-8",
    ),
    UiRuntimeAssetDefinitionV1(
        asset_code="browser_dom_driver_js",
        route="/assets/marketcore/ui-runtime/v1/browser-dom-driver.js",
        relative_path="browser_dom_driver_v1.js",
        content_type="application/javascript; charset=utf-8",
    ),
    UiRuntimeAssetDefinitionV1(
        asset_code="browser_render_tree_executor_js",
        route="/assets/marketcore/ui-runtime/v1/browser-render-tree-executor.js",
        relative_path="browser_render_tree_executor_v1.js",
        content_type="application/javascript; charset=utf-8",
    ),
    UiRuntimeAssetDefinitionV1(
        asset_code="home_runtime_switch_js",
        route="/assets/marketcore/ui-runtime/v1/home-runtime-switch.js",
        relative_path="home_runtime_switch_v1.js",
        content_type="application/javascript; charset=utf-8",
    ),
    UiRuntimeAssetDefinitionV1(
        asset_code="home_runtime_html",
        route="/workspace-v2",
        relative_path="home_runtime_v1.html",
        content_type="text/html; charset=utf-8",
    ),
)

_ASSET_BY_ROUTE = {
    definition.route: definition
    for definition in UI_RUNTIME_ASSETS_V1
}


def normalize_ui_runtime_asset_route_v1(route: str) -> str:
    if not isinstance(route, str):
        raise TypeError("UI_RUNTIME_ASSET_ROUTE_MUST_BE_STRING")

    if not route.startswith("/"):
        raise UiRuntimeAssetDeliveryErrorV1(
            f"UI_RUNTIME_ASSET_ROUTE_INVALID:{route}"
        )

    if route != "/" and route.endswith("/"):
        return route[:-1]

    return route


def resolve_ui_runtime_asset_v1(
    route: str,
) -> UiRuntimeAssetDefinitionV1 | None:
    normalized_route = normalize_ui_runtime_asset_route_v1(route)
    return _ASSET_BY_ROUTE.get(normalized_route)


def load_ui_runtime_asset_v1(
    route: str,
) -> UiRuntimeAssetResponseV1:
    definition = resolve_ui_runtime_asset_v1(route)

    if definition is None:
        return UiRuntimeAssetResponseV1(
            status_code=404,
            content_type="text/plain; charset=utf-8",
            body=b"UI_RUNTIME_ASSET_NOT_FOUND",
        )

    asset_root = _ASSET_ROOT.resolve()
    asset_path = (asset_root / definition.relative_path).resolve()

    try:
        asset_path.relative_to(asset_root)
    except ValueError as exc:
        raise UiRuntimeAssetDeliveryErrorV1(
            "UI_RUNTIME_ASSET_PATH_OUTSIDE_ROOT"
        ) from exc

    if not asset_path.is_file():
        raise UiRuntimeAssetDeliveryErrorV1(
            f"UI_RUNTIME_ASSET_FILE_NOT_FOUND:{definition.asset_code}"
        )

    return UiRuntimeAssetResponseV1(
        status_code=200,
        content_type=definition.content_type,
        body=asset_path.read_bytes(),
    )


def ui_runtime_asset_content_type_v1(
    route: str,
) -> str | None:
    definition = resolve_ui_runtime_asset_v1(route)

    if definition is None:
        return None

    return definition.content_type
