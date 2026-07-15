from __future__ import annotations

import json
from collections.abc import Callable

from marketcore.presentation.ui_runtime.asset_delivery_v1 import (
    load_ui_runtime_asset_v1,
)

from marketcore.presentation.workspace_v2.render_tree_http_v1 import (
    control_center_render_tree_http_v2,
    home_render_tree_http_v1,
    portfolio_render_tree_http_v1,
)
from marketcore.presentation.workspace_v2.render_tree_http_v2 import (
    domain_render_tree_http_v2,
)

from marketcore.presentation.workspace_v2.portfolio_page_v2 import (
    render_workspace_v2_portfolio_page_v2,
)
from marketcore.presentation.workspace_v2.edge_oos_control_center_v1 import (
    action_status_v1,
    run_hypothesis_action_v1,
    run_hypothesis_pipeline_action_v1,
    run_lead_lag_action_v1,
    run_relationship_factory_action_v2,
    run_relationship_pipeline_action_v2,
    run_signal_funnel_action_v1,
    run_data_quality_action_v1,
    run_session_execution_action_v1,
    run_edge_search_pipeline_action_v1,
    run_finam_instrument_discovery_action_v1,
    run_oos_action_v1,
    run_strategy_generator_action_v2,
    run_strategy_hypothesis_action_v2,
    run_hypothesis_lineage_action_v2,
    run_relative_strength_action_v2,
    run_intermarket_lead_lag_action_v2,
    run_failure_diagnostics_action_v2,
    run_gross_net_attribution_action_v1,
    run_targeted_trade_replay_action_v1,
    run_swing_timeframes_action_v1,
    run_swing_data_quality_action_v1,
    run_swing_factory_action_v1,
    run_forward_incubator_action_v1,
)

EDGE_OOS_SECTION_ROUTES = {
    "/workspace-v2/control-center/edge-oos/data-quality": "data-quality-gate",
    "/workspace-v2/control-center/edge-oos/commodity-factors": "commodity-factors",
    "/workspace-v2/control-center/edge-oos/discover": "hypothesis-discovery",
    "/workspace-v2/control-center/edge-oos/lead-lag": "lead-lag",
    "/workspace-v2/control-center/edge-oos/relationship-factory": "relationship-factory",
    "/workspace-v2/control-center/edge-oos/relationship-pipeline": "relationship-factory",
    "/workspace-v2/control-center/edge-oos/signal-funnel": "signal-funnel",
    "/workspace-v2/control-center/edge-oos/session-execution": "session-edge",
    "/workspace-v2/control-center/edge-oos/execution-edge": "execution-edge",
    "/workspace-v2/control-center/edge-oos/edge-search-pipeline": "relationship-factory",
    "/workspace-v2/control-center/edge-oos/finam-instruments": "finam-instruments",
    "/workspace-v2/control-center/edge-oos/strategy-generator": "strategy-generator",
    # Diagnostic actions also need a safe GET route: bookmarked operator links must not 404.
    "/workspace-v2/control-center/edge-oos/failure-diagnostics": "strategy-generator",
}


PageHandler = Callable[[], str]


def _control_center_runtime_response() -> tuple[int, bytes]:
    response = load_ui_runtime_asset_v1("/workspace-v2/control-center/edge-oos")
    return response.status_code, response.body


class ReadOnlyRouter:
    """Compatibility router for the standalone read-only status UI."""

    def __init__(self) -> None:
        self._routes: list[tuple[str, PageHandler]] = []

    def register(self, prefix: str, handler: PageHandler) -> None:
        self._routes.append((prefix, handler))
        self._routes.sort(key=lambda item: len(item[0]), reverse=True)

    def resolve(self, path: str) -> PageHandler | None:
        clean_path = path.split("?", 1)[0]
        for prefix, handler in self._routes:
            if clean_path.startswith(prefix):
                return handler
        return None


def route(path: str, query: dict[str, list[str]] | None = None) -> tuple[int, bytes]:
    query = query or {}
    domain_render_tree_routes = {
        "/api/v2/domain-render-tree/home": "HOME",
        "/api/v2/domain-render-tree/portfolio": "PORTFOLIO",
        "/api/v2/domain-render-tree/control-center": "CONTROL_CENTER",
    }
    producer_code = domain_render_tree_routes.get(path.rstrip("/"))
    if producer_code is not None:
        response = domain_render_tree_http_v2(
            producer_code,
            timezone_code=(query.get("timezone") or [None])[0],
        )
        return response.status_code, response.body
    if path == "/api/v1/control-center/action-status":
        action_code = (query.get("action") or [""])[0]
        return 200, json.dumps(action_status_v1(action_code), ensure_ascii=False).encode("utf-8")
    if path in ("/api/v2/render-tree/control-center/edge", "/api/v2/render-tree/control-center/edge/"):
        response = control_center_render_tree_http_v2()
        return response.status_code, response.body
    if path in (
        "/workspace-v2",
        "/workspace-v2/",
    ):
        response = load_ui_runtime_asset_v1(
            "/workspace-v2"
        )
        return response.status_code, response.body

    if path == "/":
        response = load_ui_runtime_asset_v1(
            "/workspace-v2"
        )
        return response.status_code, response.body

    if path.startswith("/assets/marketcore/ui-runtime/v1/"):
        response = load_ui_runtime_asset_v1(path)
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/home",
        "/api/v1/render-tree/home/",
    ):
        response = home_render_tree_http_v1()
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/portfolio",
        "/api/v1/render-tree/portfolio/",
    ):
        response = portfolio_render_tree_http_v1()
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/portfolio/phone",
        "/api/v1/render-tree/portfolio/phone/",
    ):
        response = portfolio_render_tree_http_v1(
            theme_code="PHONE",
        )
        return response.status_code, response.body

    if path in (
        "/api/v1/render-tree/portfolio/tablet",
        "/api/v1/render-tree/portfolio/tablet/",
    ):
        response = portfolio_render_tree_http_v1(
            theme_code="TABLET",
        )
        return response.status_code, response.body


    if path in ("/workspace-v2/portfolio", "/workspace-v2/portfolio/"):
        return 200, render_workspace_v2_portfolio_page_v2(
            timezone=(query.get("timezone") or [None])[0],
            currency=(query.get("currency") or [None])[0],
            broker=(query.get("broker") or [None])[0],
        ).encode("utf-8")

    if path in ("/workspace-v2/control-center/edge-oos", "/workspace-v2/control-center/edge-oos/"):
        return _control_center_runtime_response()

    if path in ("/workspace-v2/control-center/edge-oos/legacy", "/workspace-v2/control-center/edge-oos/legacy/"):
        return _control_center_runtime_response()

    if path in EDGE_OOS_SECTION_ROUTES:
        return _control_center_runtime_response()


    if path in ("/workspace-v2/portfolio/phone",):
        return (
            200,
            render_workspace_v2_portfolio_page_v2(
                theme_code="PHONE",
            ).encode("utf-8"),
        )

    if path in ("/workspace-v2/portfolio/tablet",):
        return (
            200,
            render_workspace_v2_portfolio_page_v2(
                theme_code="TABLET",
            ).encode("utf-8"),
        )

    return 404, b"Not found"


def route_post(path: str) -> tuple[int, bytes]:
    actions: dict[str, Callable[[], str]] = {
        "/workspace-v2/control-center/edge-oos/forward-incubator": run_forward_incubator_action_v1,
        "/workspace-v2/control-center/edge-oos/swing-timeframes": run_swing_timeframes_action_v1,
        "/workspace-v2/control-center/edge-oos/swing-data-quality": run_swing_data_quality_action_v1,
        "/workspace-v2/control-center/edge-oos/swing-factory": run_swing_factory_action_v1,
        "/workspace-v2/control-center/edge-oos/targeted-trade-replay": run_targeted_trade_replay_action_v1,
        "/workspace-v2/control-center/edge-oos/gross-net-attribution": run_gross_net_attribution_action_v1,
        "/workspace-v2/control-center/edge-oos/failure-diagnostics": run_failure_diagnostics_action_v2,
        "/workspace-v2/control-center/edge-oos/intermarket-lead-lag-run": run_intermarket_lead_lag_action_v2,
        "/workspace-v2/control-center/edge-oos/relative-strength-run": run_relative_strength_action_v2,
        "/workspace-v2/control-center/edge-oos/hypothesis-lineage": run_hypothesis_lineage_action_v2,
        "/workspace-v2/control-center/edge-oos/strategy-hypothesis-run": run_strategy_hypothesis_action_v2,
        "/workspace-v2/control-center/edge-oos/strategy-generator": run_strategy_generator_action_v2,
        "/workspace-v2/control-center/edge-oos/hypothesis-pipeline": run_hypothesis_pipeline_action_v1,
        "/workspace-v2/control-center/edge-oos/finam-instruments": run_finam_instrument_discovery_action_v1,
        "/workspace-v2/control-center/edge-oos/data-quality": run_data_quality_action_v1,
        "/workspace-v2/control-center/edge-oos/session-execution": run_session_execution_action_v1,
        "/workspace-v2/control-center/edge-oos/edge-search-pipeline": run_edge_search_pipeline_action_v1,
        "/workspace-v2/control-center/edge-oos/run": run_oos_action_v1,
        "/workspace-v2/control-center/edge-oos/discover": run_hypothesis_action_v1,
        "/workspace-v2/control-center/edge-oos/lead-lag": run_lead_lag_action_v1,
        "/workspace-v2/control-center/edge-oos/relationship-factory": run_relationship_factory_action_v2,
        "/workspace-v2/control-center/edge-oos/relationship-pipeline": run_relationship_pipeline_action_v2,
        "/workspace-v2/control-center/edge-oos/signal-funnel": run_signal_funnel_action_v1,
    }
    action = actions.get(path)
    if action is None:
        return 404, b"Not found"
    action()
    return _control_center_runtime_response()
