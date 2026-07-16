from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def test_intraday_missing_timestamps_render_as_localized_unavailable() -> None:
    document = build_domain_document_v2("INTRADAY", timezone_code="Europe/Moscow")
    values = [node.content for node in _walk(document.root) if node.node_type is RenderNodeTypeV2.METRIC_VALUE]
    assert values
    assert all(content is not None for content in values)
    assert all(content.message_key is not None or content.value is not None for content in values)
