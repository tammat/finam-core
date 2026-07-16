from marketcore.presentation.render_tree.v2 import ActionKindV2, RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_control_center_uses_canonical_ten_stage_profit_funnel() -> None:
    document = build_domain_document_v2("CONTROL_CENTER", timezone_code="Europe/Moscow")
    nodes = tuple(_walk(document.root))
    rows = [node for node in nodes if node.node_type is RenderNodeTypeV2.TABLE_ROW and node.node_id.startswith("control.section.funnel.row.")]
    assert len(rows) == 10
    assert all(len(row.children) == 11 for row in rows)
    values = [[cell.content.value for cell in row.children] for row in rows]
    assert [row[0] for row in values] == [
        "RESEARCH","CANDIDATE","VALIDATED_EDGE","OOS","FORWARD",
        "SHADOW","PAPER","RUNTIME","LIVE","PROFIT",
    ]
    assert isinstance(values[3][1], int) and values[3][1] >= 0
    if values[3][1] == 0:
        assert values[3][2] in {None, 0.0}
    else:
        assert 0.0 <= values[3][2] <= 100.0
    assert values[-2][1] == 0
    assert values[-1][1] == 0


def test_control_center_funnel_exposes_source_freshness_and_reason() -> None:
    document = build_domain_document_v2("CONTROL_CENTER")
    rows = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.TABLE_ROW and node.node_id.startswith("control.section.funnel.row.")]
    for row in rows:
        by_column = {cell.content.column_code: cell.content.value for cell in row.children}
        assert by_column["source_identity"]
        assert by_column["freshness_code"] in {"CURRENT","STALE","UNAVAILABLE"}
        assert by_column["quality_code"] in {"VERIFIED","UNVERIFIED","UNAVAILABLE"}
        assert by_column["reason_code"]


def test_control_center_funnel_rows_open_stage_owner_on_double_click() -> None:
    document = build_domain_document_v2("CONTROL_CENTER")
    rows = [node for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.TABLE_ROW and node.node_id.startswith("control.section.funnel.row.")]
    targets = {
        row.children[0].content.value: row.action.target_id
        for row in rows
    }
    assert all(row.action.action_kind is ActionKindV2.NAVIGATE for row in rows)
    assert targets == {
        "RESEARCH": "container.research", "CANDIDATE": "container.research",
        "VALIDATED_EDGE": "container.edge", "OOS": "container.edge",
        "FORWARD": "container.intraday", "SHADOW": "container.intraday",
        "PAPER": "container.intraday", "RUNTIME": "container.intraday",
        "LIVE": "container.intraday", "PROFIT": "container.capital",
    }
