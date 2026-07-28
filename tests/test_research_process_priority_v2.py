from pathlib import Path


def test_research_audit_shows_localized_process_name() -> None:
    domain = Path(
        "src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py"
    ).read_text(encoding="utf-8")
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py"
    ).read_text(encoding="utf-8")
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
    ).read_text(encoding="utf-8")
    migration = Path(
        "sql/presentation/177_research_process_priority_i18n_v1.sql"
    ).read_text(encoding="utf-8")

    assert "process_type: str" in domain
    assert "p.process_id,p.process_type,p.run_id" in resolver
    assert 'columns=("status","process","started"' in renderer
    assert "item.process_type" in renderer
    assert "research.audit.column.process" in migration
    assert "research.domain.edge_search" in migration
    assert "research.domain.research_refresh" in migration


def test_failed_process_can_be_requeued_at_maximum_priority() -> None:
    driver = Path(
        "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js"
    ).read_text(encoding="utf-8")
    handler = Path("src/marketcore/action/handler_registry_v2.py").read_text(encoding="utf-8")

    assert "Повторить срочно" in driver
    assert 'targetId: "MAX_PRIORITY"' in driver
    assert 'str(intent.target_id or "").strip().upper() == "MAX_PRIORITY"' in handler
    assert "SET priority=1" in handler


def test_operator_deadline_and_automatic_action_are_unambiguous() -> None:
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py"
    ).read_text(encoding="utf-8")
    migration = Path(
        "sql/presentation/177_research_process_priority_i18n_v1.sql"
    ).read_text(encoding="utf-8")
    assert 'next_key = "home.operator.next.automatic"' in renderer
    assert 'next_key = "home.operator.next.review_block"' in renderer
    assert "'column.operator.deadline','ru','Срок до'" in migration
