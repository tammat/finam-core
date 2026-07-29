from marketcore.presentation.render_tree.v2 import RenderNodeTypeV2
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def test_home_is_three_short_sections_with_one_action() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    nodes = list(walk(document.root))
    sections = [node.node_id for node in nodes if node.node_type is RenderNodeTypeV2.SECTION]
    assert sections == ["home.compact.now", "home.compact.progress", "home.compact.attention"]
    actions = [node for node in nodes if node.node_type is RenderNodeTypeV2.ACTION]
    assert len(actions) == 1
    assert actions[0].action.command_code == "RESEARCH.REQUEST_REFRESH"


def test_home_uses_plain_russian_and_no_operator_table() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    nodes = list(walk(document.root))
    values = [str(node.content.value) for node in nodes if node.content and node.content.value]
    text = " ".join(values)
    for phrase in ("Сейчас", "Прогресс", "Нужно внимание", "Реальные сделки", "Выключены"):
        assert phrase in text
    assert "home.operator.actions.table" not in {node.node_id for node in nodes}
    assert not any(word in text for word in ("LONG", "SHORT", "OOS", "Paper", "exact"))


def test_home_progress_is_bounded_to_six_rows() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    nodes = list(walk(document.root))
    progress = next(node for node in nodes if node.node_id == "home.compact.progress")
    metric_list = next(child for child in progress.children if child.node_type is RenderNodeTypeV2.METRIC_LIST)
    metric_rows = [child for child in metric_list.children if child.node_type is RenderNodeTypeV2.METRIC_ROW]
    assert 4 <= len(metric_rows) <= 7


def test_home_explains_compact_universe_coverage() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    values = [
        str(node.content.value)
        for node in walk(document.root)
        if node.content and node.content.value
    ]
    coverage = next(value for value in values if value.startswith("активно "))
    assert "сделки есть у" in coverage
    assert "на экране топ-" in coverage


def test_home_uses_russian_instrument_names_with_ticker() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    values = [
        str(node.content.value)
        for node in walk(document.root)
        if node.content and node.content.value
    ]
    progress_labels = [value for value in values if " · покупка" in value or " · продажа" in value]
    assert progress_labels
    assert all("(" in value and ")" in value for value in progress_labels)
    assert any(any(char in value for char in "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ") for value in progress_labels)


def test_metric_sections_survive_browser_empty_section_cleanup() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    nodes = {node.node_id: node for node in walk(document.root)}
    for section_id in ("home.compact.now", "home.compact.progress"):
        assert any(
            child.node_type is RenderNodeTypeV2.METRIC_LIST
            for child in nodes[section_id].children
        )


def test_attention_ignores_historical_failure_counter() -> None:
    source = open(
        "src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py",
        encoding="utf-8",
    ).read()
    section = source[source.index("def _attention_section"):source.index("def render_home_compact_v1")]
    assert "failed_24h" not in section
    assert "process_failed" in section and "data_stale" in section


def test_home_explains_data_quality_in_one_short_line() -> None:
    document = build_domain_document_v2("HOME", timezone_code="Europe/Moscow")
    values = [
        str(node.content.value)
        for node in walk(document.root)
        if node.content and node.content.value
    ]
    quality = next(value for value in values if value.startswith("свежие "))
    assert "задержка" in quality and "вне сессии" in quality
