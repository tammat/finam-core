from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class UiRuntimeAssetDeliveryErrorV2(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UiRuntimeAssetDefinitionV2:
    asset_code: str
    route: str
    relative_path: str
    content_type: str = "application/javascript; charset=utf-8"


@dataclass(frozen=True, slots=True)
class UiRuntimeAssetResponseV2:
    status_code: int
    content_type: str
    body: bytes


_ASSET_ROOT = Path(__file__).resolve().parent / "assets" / "v2"

UI_RUNTIME_ASSETS_V2: tuple[UiRuntimeAssetDefinitionV2, ...] = (
    UiRuntimeAssetDefinitionV2("render_tree_validator", "/assets/marketcore/ui-runtime/v2/render-tree-validator.js", "render_tree_validator_v2.js"),
    UiRuntimeAssetDefinitionV2("domain_render_tree_runtime", "/assets/marketcore/ui-runtime/v2/domain-render-tree-runtime.js", "domain_render_tree_runtime_v2.js"),
    UiRuntimeAssetDefinitionV2("browser_platform_driver", "/assets/marketcore/ui-runtime/v2/browser-platform-driver.js", "browser_platform_driver_v2.js"),
    UiRuntimeAssetDefinitionV2("browser_bootstrap", "/assets/marketcore/ui-runtime/v2/browser-bootstrap.js", "browser_bootstrap_v2.js"),
    UiRuntimeAssetDefinitionV2("browser_presentation_services", "/assets/marketcore/ui-runtime/v2/browser-presentation-services.js", "browser_presentation_services_v2.js"),
    UiRuntimeAssetDefinitionV2("browser_action_controller", "/assets/marketcore/ui-runtime/v2/browser-action-controller.js", "browser_action_controller_v2.js"),
)

_ASSET_BY_ROUTE = {asset.route: asset for asset in UI_RUNTIME_ASSETS_V2}


def resolve_ui_runtime_asset_v2(route: str) -> UiRuntimeAssetDefinitionV2 | None:
    if not isinstance(route, str):
        raise TypeError("UI_RUNTIME_V2_ASSET_ROUTE_MUST_BE_STRING")
    if not route.startswith("/"):
        raise UiRuntimeAssetDeliveryErrorV2("UI_RUNTIME_V2_ASSET_ROUTE_INVALID")
    return _ASSET_BY_ROUTE.get(route[:-1] if route.endswith("/") else route)


def load_ui_runtime_asset_v2(route: str) -> UiRuntimeAssetResponseV2:
    definition = resolve_ui_runtime_asset_v2(route)
    if definition is None:
        return UiRuntimeAssetResponseV2(404, "text/plain; charset=utf-8", b"UI_RUNTIME_V2_ASSET_NOT_FOUND")
    asset_root = _ASSET_ROOT.resolve()
    asset_path = (asset_root / definition.relative_path).resolve()
    try:
        asset_path.relative_to(asset_root)
    except ValueError as exc:
        raise UiRuntimeAssetDeliveryErrorV2("UI_RUNTIME_V2_ASSET_PATH_OUTSIDE_ROOT") from exc
    if not asset_path.is_file():
        raise UiRuntimeAssetDeliveryErrorV2(f"UI_RUNTIME_V2_ASSET_FILE_NOT_FOUND:{definition.asset_code}")
    return UiRuntimeAssetResponseV2(200, definition.content_type, asset_path.read_bytes())


def ui_runtime_asset_content_type_v2(route: str) -> str | None:
    definition = resolve_ui_runtime_asset_v2(route)
    return None if definition is None else definition.content_type
