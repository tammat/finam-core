from __future__ import annotations

import inspect

from marketcore.presentation.workspace_v2.renderer import (
    research_v2_domain_renderer,
)
from marketcore.presentation.workspace_v2.resolver import (
    ngu6_frozen_day_oos_status_v1,
)


def test_ngu6_oos_resolver_has_no_write_operations():
    source = inspect.getsource(
        ngu6_frozen_day_oos_status_v1
    )

    forbidden = (
        "systemctl start",
        "systemctl restart",
        "systemctl enable",
        "systemctl stop",
        "DELETE FROM",
        "UPDATE ",
        "INSERT INTO",
        "--write",
        "run_ngu6_frozen_day_oos_monitor_v1.py",
    )

    for token in forbidden:
        assert token not in source


def test_ngu6_oos_panel_has_no_render_actions():
    source = inspect.getsource(
        research_v2_domain_renderer._ngu6_oos_panel
    )

    assert "RenderActionV2(" not in source
    assert "ActionKindV2." not in source


def test_ngu6_oos_panel_is_registered_in_research():
    source = inspect.getsource(
        research_v2_domain_renderer
        .render_research_domain_v2
    )

    assert "children.extend(_ngu6_oos_panel())" in source


def test_oos3_boundary_is_frozen():
    assert (
        ngu6_frozen_day_oos_status_v1.OOS3_BOUNDARY
        == "2026-08-08T12:45:00+00:00"
    )


def test_dataset_version_is_frozen():
    assert (
        ngu6_frozen_day_oos_status_v1.DATASET_VERSION
        == "NATIVE_FINAM_M5_V1"
    )
