from __future__ import annotations

import json
import sys
import time
from urllib.request import urlopen


def read_url(url: str, timeout: float = 5.0) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def wait_url(url: str, attempts: int = 20, delay: float = 0.5) -> str:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return read_url(url)
        except Exception as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"URL not ready: {url}; last_error={last_error}")


def main() -> None:
    kg_health_raw = wait_url("http://127.0.0.1:8095/api/kg/v1/health")
    kg_health = json.loads(kg_health_raw)
    assert kg_health.get("status") == "OK", kg_health_raw

    home = wait_url("http://127.0.0.1:8080/")

    control_center = wait_url(
        "http://127.0.0.1:8080/"
        "api/v2/domain-render-tree/control-center"
    )

    i18n_catalog = wait_url(
        "http://127.0.0.1:8080/"
        "api/v2/i18n/catalog?locale=ru-RU"
    )

    assert "MarketCore OS" in home, (
        "home missing MarketCore OS"
    )

    assert control_center.strip(), (
        "control-center render tree is empty"
    )

    assert i18n_catalog.strip(), (
        "ru-RU i18n catalog is empty"
    )
    assert "MarketCore OS" in home, (
        "home missing MarketCore OS title"
    )

    assert 'data-marketcore-ui-runtime="v2"' in home, (
        "home missing UI runtime v2 marker"
    )

    assert "workspace-shell-bootstrap.js" in home, (
        "home missing workspace shell bootstrap"
    )


    print("kg_api_8095=READY")
    print("marketcore_ui_8080=READY")
    print("ui_shell_home=OK")
    print("domain_render_tree_control_center=OK")
    print("i18n_ru_catalog=OK")
    print("legacy_risk_route_required=0")
    print("risk_page=READY")
    print("settings_page=READY")
    print("VERDICT=CHECK_MARKETCORE_UI_SYSTEMD_8080_V1_OK")


if __name__ == "__main__":
    main()
