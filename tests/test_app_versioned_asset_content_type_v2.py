from io import BytesIO
from types import SimpleNamespace

from marketcore.presentation.app import MarketCoreUiHandler


def test_versioned_css_keeps_css_content_type() -> None:
    headers = {}
    response = SimpleNamespace(
        path="/assets/marketcore/ui-runtime/v2/workspace.css?v=20260716.2",
        wfile=BytesIO(),
        send_response=lambda code: None,
        send_header=lambda key, value: headers.__setitem__(key, value),
        end_headers=lambda: None,
    )
    MarketCoreUiHandler._send_html(response, 200, b"body{}")
    assert headers["Content-Type"] == "text/css; charset=utf-8"
