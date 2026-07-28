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


def test_edge_control_has_only_two_contextual_buttons() -> None:
    source = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py").read_text()
    section = source[source.index("def _edge_control_section"):source.index("def _freshness_section")]
    assert section.count("_command(") == 3  # two alternatives for one slot + refresh
    assert "universe_include" not in section
    assert "universe_exclude" not in section
    assert "universe_priority" not in section


def test_manual_control_does_not_disable_or_cancel_autorun() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    worker = (ROOT / "src/marketcore/action/command_worker_v2.py").read_text()
    assert "EDGE_SEARCH_AUTO_ENQUEUE_V1" in resolver
    assert "edge_manual_pending" in resolver
    assert "actor_id<>'system.scheduler'" in worker
    assert "actor_id=%s" in worker
