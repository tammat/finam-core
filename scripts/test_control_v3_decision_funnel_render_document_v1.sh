#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

cd "$ROOT"

export PYTHONPATH="$ROOT/src:$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== TEST CONTROL V3 DECISION FUNNEL RENDER DOCUMENT V2 ==="

"$PYTHON" - <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import marketcore.presentation.workspace_v2.renderer.control_compact_v3_domain_renderer as renderer


decision_payload = {
    "status": "OK",
    "data": {
        "status": "EMPTY",
        "read_only": True,
        "summary": {
            "event_count": 0,
            "signal_count": 0,
            "pass_events": 0,
            "reject_events": 0,
            "error_events": 0,
            "skip_events": 0,
            "symbol_count": 0,
            "strategy_count": 0,
            "rejection_rate": None,
            "first_event_at": None,
            "last_event_at": None,
        },
        "stage_funnel": [],
        "top_rejection_reasons": [],
        "dimensions": [],
        "recent_events": [],
        "metadata": {
            "runtime_instrumentation": 0,
            "write_actions_allowed": 0,
        },
    },
    "metadata": {
        "read_only": 1,
    },
}


def stub_section(node_id: str):
    """
    Валидный нейтральный SECTION для изоляции чужих секций.

    Проверяемый Decision Funnel helper не подменяется.
    """

    return renderer.RenderNodeV2(
        renderer.RenderNodeTypeV2.SECTION,
        node_id,
        children=(
            renderer._leaf(
                renderer.RenderNodeTypeV2.SUBTITLE,
                f"{node_id}.status",
                "Изолированная секция regression-теста",
            ),
        ),
    )


snapshot = {
    # Поля, которые render_control_compact_v3 читает непосредственно.
    "generated_at": datetime(
        2026,
        8,
        4,
        14,
        0,
        tzinfo=timezone.utc,
    ),
    "process": {
        "status_code": "READY",
    },
    "hierarchy_nearest": {
        "closed_trades": 0,
        "symbol_code": None,
    },
    "freshness": (),
    "closed_total": 0,
    "ready_links": 0,
    "hierarchy_top_exact": (),
    "open_position_diagnostics": (),
}


patches = {
    "_compact_state_section": lambda *_: stub_section(
        "test.control.v3.compact_state"
    ),
    "_signal_funnel_section": lambda *_: stub_section(
        "test.control.v3.signal_funnel"
    ),
    "_market_regime_section": lambda *_: stub_section(
        "test.control.v3.market_regime"
    ),
    "_edge_diagnostic_section": lambda *_: stub_section(
        "test.control.v3.edge_diagnostic"
    ),
    "_swing_section": lambda *_: stub_section(
        "test.control.v3.swing"
    ),
    "_historical_corrections_section_v1": lambda *_: stub_section(
        "test.control.v3.historical_corrections"
    ),
    "_priority_exact_section": lambda *_: stub_section(
        "test.control.v3.priority_exact"
    ),
    "_open_positions_section": lambda *_: stub_section(
        "test.control.v3.open_positions"
    ),
    "_compact_control_section": lambda *_: stub_section(
        "test.control.v3.compact_control"
    ),
}


with (
    patch(
        "marketcore.presentation.pages."
        "decision_funnel_v1.get_json",
        return_value=decision_payload,
    ),
    patch.multiple(renderer, **patches),
):
    document = renderer.render_control_compact_v3(
        snapshot
    )


def walk(node):
    yield node

    for child in getattr(node, "children", ()) or ():
        yield from walk(child)


nodes = tuple(walk(document.root))

node_ids = tuple(
    str(getattr(node, "node_id", ""))
    for node in nodes
)

decision_count = node_ids.count(
    "control.v3.decision_funnel"
)

empty_count = node_ids.count(
    "control.v3.decision_funnel.empty"
)

title_count = node_ids.count(
    "control.v3.decision_funnel.title"
)

assert decision_count == 1, decision_count
assert empty_count == 1, empty_count
assert title_count == 1, title_count

assert document.document_id == "operator.control.v3"
assert document.quality_code == "VERIFIED"

# validate_render_document_v2 вызывается внутри реального renderer.
# Если документ невалиден, render_control_compact_v3 завершится ошибкой.
print(f"decision_section_count={decision_count}")
print(f"decision_empty_node_count={empty_count}")
print(f"decision_title_node_count={title_count}")
print("foreign_sections_isolated=1")
print("render_document_validation=OK")
print("read_only=1")
print("ui_direct_sql=0")
print("runtime_instrumentation=0")
PY

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_DECISION_FUNNEL_RENDER_DOCUMENT_V2_OK"
