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


def test_ngu6_oos_panel_valid_when_dataset_unavailable(monkeypatch):
    from marketcore.presentation.render_tree.v2.validation import (
        validate_render_document_v2,
    )
    from marketcore.presentation.workspace_v2.resolver import (
        ngu6_frozen_day_oos_status_v1 as status_module,
    )

    def unavailable():
        raise RuntimeError("dataset_unavailable_for_test")

    monkeypatch.setattr(
        status_module,
        "_load_canonical_dataset",
        unavailable,
    )

    document = (
        research_v2_domain_renderer
        .render_research_domain_v2(
            __import__(
                "marketcore.presentation.workspace_v2.resolver."
                "research_v2_resolver",
                fromlist=["ResearchV2Resolver"],
            ).ResearchV2Resolver().resolve(),
            timezone_code="Europe/Moscow",
        )
    )

    validate_render_document_v2(document)


def test_ngu6_oos_panel_has_compact_status_bar():
    source = inspect.getsource(
        research_v2_domain_renderer._ngu6_oos_panel
    )

    assert "research.ngu6_oos.status_bar" in source
    assert "RenderNodeTypeV2.BADGE" in source
    assert "NO NEW TRADE" in source


def test_ngu6_oos_empty_events_are_not_rendered_as_empty_table(
    monkeypatch,
):
    from dataclasses import replace

    from marketcore.presentation.workspace_v2.resolver import (
        ngu6_frozen_day_oos_status_v1 as status_module,
    )

    current = (
        status_module
        .resolve_ngu6_frozen_day_oos_status_v1()
    )

    monkeypatch.setattr(
        research_v2_domain_renderer,
        "resolve_ngu6_frozen_day_oos_status_v1",
        lambda: replace(
            current,
            events=(),
        ),
    )

    nodes = (
        research_v2_domain_renderer
        ._ngu6_oos_panel()
    )

    def walk(node):
        yield node
        for child in node.children:
            yield from walk(child)

    ids = {
        item.node_id
        for root in nodes
        for item in walk(root)
    }

    assert (
        "research.ngu6_oos.events.empty"
        in ids
    )
    assert (
        "research.ngu6_oos.events"
        not in ids
    )


def test_inventory_state_comes_from_freeze_store(
    tmp_path,
    monkeypatch,
):
    import json

    from marketcore.presentation.workspace_v2.resolver import (
        ngu6_frozen_day_oos_status_v1 as status_module,
    )

    freeze_dir = tmp_path / "freeze"
    freeze_dir.mkdir()

    identity_sha = "a" * 64

    artifact = {
        "freezer_version": (
            "NGU6_FROZEN_DAY_OOS_INVENTORY_FREEZER_V1"
        ),
        "frozen_at_utc": (
            "2026-08-10T13:10:00+00:00"
        ),
        "symbol": "NGU6@RTSX",
        "timeframe": "M5",
        "dataset_version": "NATIVE_FINAM_M5_V1",
        "dataset_rows": 9000,
        "dataset_last": (
            "2026-08-10T13:00:00+00:00"
        ),
        "oos3_boundary": (
            "2026-08-08T12:45:00+00:00"
        ),
        "new_completed_day_trades": 1,
        "trade_identities": [
            (
                "1|2026-08-10T10:00:00+00:00|"
                "LONG|2026-08-10T10:25:00+00:00|219"
            )
        ],
        "inventory_frozen": True,
        "pnl_revealed": False,
        "parameter_search": False,
        "strategy_changed": False,
        "monitor_verdict": (
            "NEW_FROZEN_DAY_INVENTORY_READY"
        ),
        "identity_sha256": identity_sha,
    }

    (
        freeze_dir
        / f"inventory_{identity_sha}.json"
    ).write_text(
        json.dumps(artifact),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        status_module,
        "FREEZE_DIR",
        freeze_dir,
    )

    monkeypatch.setattr(
        status_module,
        "_journal_lines",
        lambda: [
            "INVENTORY_FROZEN=0",
            "PNL_REVEALED=0",
            "VERDICT=NO_NEW_FROZEN_DAY_TRADES",
        ],
    )

    status = (
        status_module
        .resolve_ngu6_frozen_day_oos_status_v1()
    )

    assert status.inventory_frozen is True
    assert status.freeze_artifact_count == 1
    assert status.latest_frozen_trade_count == 1
    assert (
        status.latest_freeze_identity_sha256
        == identity_sha
    )

    assert any(
        event.event_type
        == "INVENTORY_FROZEN"
        for event in status.events
    )


def test_journal_inventory_flag_cannot_fake_freeze(
    tmp_path,
    monkeypatch,
):
    from marketcore.presentation.workspace_v2.resolver import (
        ngu6_frozen_day_oos_status_v1 as status_module,
    )

    monkeypatch.setattr(
        status_module,
        "FREEZE_DIR",
        tmp_path / "absent",
    )

    monkeypatch.setattr(
        status_module,
        "_journal_lines",
        lambda: [
            "INVENTORY_FROZEN=1",
            "PNL_REVEALED=0",
            "VERDICT=NO_NEW_FROZEN_DAY_TRADES",
        ],
    )

    status = (
        status_module
        .resolve_ngu6_frozen_day_oos_status_v1()
    )

    assert status.inventory_frozen is False
    assert status.freeze_artifact_count == 0
    assert status.latest_frozen_trade_count == 0
    assert (
        status.latest_freeze_identity_sha256
        == "NONE"
    )
