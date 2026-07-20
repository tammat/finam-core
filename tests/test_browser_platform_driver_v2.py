from pathlib import Path
from types import SimpleNamespace

from marketcore.presentation.app import MarketCoreUiHandler


def test_rows_and_clickable_containers_require_double_click() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'const isTableRow = node.type === "table_row";' in source
    assert 'const isContainer = node.type === "card";' in source
    assert "const requiresDoubleClick = isTableRow || isContainer || isCommandButton;" in source
    assert 'if (isResearchRow && isRecommendation) this.openResearchActions(element);' in source
    assert 'else this.openRecommendedActions(element);' in source
    assert 'element.addEventListener("dblclick", () => node.node_id.startsWith("home.operator.")' in source
    assert '? this.openOperatorCardActions(element,emit)' in source
    assert 'if (isTableRow) this.openRecommendedActions(element);' in source
    assert 'else if (isContainer && node.node_id.startsWith("home.operator.")) this.openOperatorCardActions(element,emit);' in source
    assert 'else if (isContainer) this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…");' in source
    assert 'else emit("CLICK");' in source


def test_action_controller_can_create_uuid_on_insecure_http_origin() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_action_controller_v2.js").read_text()
    assert 'typeof globalObject.crypto.randomUUID === "function"' in source
    assert "globalObject.crypto.getRandomValues(bytes)" in source
    assert "globalObject.Math.random()" in source
    assert "bytes[6] = (bytes[6] & 0x0f) | 0x40" in source
    assert "bytes[8] = (bytes[8] & 0x3f) | 0x80" in source


def test_same_origin_action_accepts_webview_without_fetch_metadata() -> None:
    request = SimpleNamespace(
        headers={"Host": "onezh.ddns.net:8080", "Origin": "http://onezh.ddns.net:8080"},
        client_address=("192.0.2.10", 12345),
    )
    assert MarketCoreUiHandler._is_same_origin_action_request(request)


def test_action_origin_must_still_match_host() -> None:
    request = SimpleNamespace(
        headers={"Host": "onezh.ddns.net:8080", "Origin": "https://attacker.example"},
        client_address=("192.0.2.10", 12345),
    )
    assert not MarketCoreUiHandler._is_same_origin_action_request(request)
def test_clickable_cards_highlight_and_open_only_on_double_click() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert 'const isContainer = node.type === "card"' in source
    assert 'this.openOperatorCardActions(element,emit)' in source
    assert 'this.activateInteractive(element,emit,"DOUBLE_CLICK","Открываю раздел…")' in source
    assert '[data-mc-node="card"][data-mc-action-id]:not([disabled]):hover' in css
    assert 'cursor: pointer' in css


def test_command_buttons_require_confirmed_double_click() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'const isCommandButton = node.type === "action"' in source
    assert 'isTableRow || isContainer || isCommandButton' in source
    assert 'globalObject.confirm("Подтвердить выполнение действия?")' in source
    assert 'activateInteractive(element,emit,"DOUBLE_CLICK","Выполняю действие…")' in source


def test_control_center_tables_are_grouped_under_collapsible_sections() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "groupControlCenterSections" in source
    assert 'code:"process"' in source
    assert 'code:"funnel"' in source
    assert 'code:"execution"' in source
    assert 'code:"methodology"' in source
    assert 'details.className = "mc-control-section-group"' in source
