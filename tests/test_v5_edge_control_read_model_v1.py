from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_control_center_registry_uses_canonical_compact_v3() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py").read_text()
    assert "ControlCompactV3Resolver().resolve()" in source
    assert "render_control_compact_v3(" in source


def test_edge_control_read_model_contains_queue_jobs_and_v5_freshness() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    assert "marketcore_action.command_request_v2" in source
    assert "analytics.system_job_run_v1" in source
    assert "('BRQ6@RTSX','M1')" in source
    assert "('VTBR@MISX','M5')" in source


def test_edge_control_only_exposes_governed_research_actions() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    expected = (
        "RESEARCH.RUN_EDGE_SEARCH",
        "RESEARCH.CANCEL_EDGE_SEARCH",
        "RESEARCH.REQUEST_REFRESH",
    )
    for command in expected:
        assert command in source
    assert "BROKER.SUBMIT_ORDER" not in source
    assert "MICRO_LIVE" not in source


def test_main_control_has_one_refresh_button() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    page = source[source.index("page = RenderNodeV2"):source.index("root = RenderNodeV2")]
    assert "_compact_control_section(snapshot)" in page
    assert "_edge_control_section(snapshot)" not in page
    section = source[source.index("def _compact_control_section"):source.index("def _priority_exact_section")]
    assert section.count("_command(") == 1
    assert "RESEARCH.REQUEST_REFRESH" in section
    assert "RESEARCH.RUN_EDGE_SEARCH" not in section


def test_manual_control_does_not_disable_or_cancel_autorun() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    worker = (ROOT / "src/marketcore/action/command_worker_v2.py").read_text()
    assert "EDGE_SEARCH_AUTO_ENQUEUE_V1" in resolver
    assert "edge_manual_pending" in resolver
    assert "actor_id<>'system.scheduler'" in worker
    assert "actor_id=%s" in worker


def test_control_center_exposes_top_five_exact_without_hierarchy_noise() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    assert "FRESH_V5_CONFIRM" in resolver
    assert "EXACT_CONTEXT" in resolver
    assert "hierarchy_top_exact" in resolver
    page = renderer[renderer.index("page = RenderNodeV2"):renderer.index("root = RenderNodeV2")]
    assert "_priority_exact_section" in page
    assert "_hierarchy_section(snapshot)" not in page
    section = renderer[renderer.index("def _priority_exact_section"):renderer.index("def _compact_state_section")]
    assert "_command(" not in section


def test_main_page_has_five_cards_and_no_technical_sections() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    body = source[source.index("cards = RenderNodeV2"):source.index("page = RenderNodeV2")]
    assert body.count("_card(") == 5
    page = source[source.index("page = RenderNodeV2"):source.index("root = RenderNodeV2")]
    for hidden in ("_jobs_section", "_freshness_section", "_branch_plan_section", "_scope_section"):
        assert hidden not in page
