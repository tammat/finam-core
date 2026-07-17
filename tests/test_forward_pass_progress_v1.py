from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_stage_is_database_driven_and_has_six_steps() -> None:
    migration = read("sql/analytics/082_forward_pass_progress_v1.sql")
    builder = read("src/scripts/build_forward_pass_progress_v1.py")
    assert "forward_pass_stage_status_v1" in migration
    assert all(f'({number},"' in builder for number in range(1, 7))
    assert "BETWEEN 0 AND 100" in migration


def test_remediation_is_future_only_and_never_uses_final_holdout() -> None:
    migration = read("sql/analytics/082_forward_pass_progress_v1.sql")
    generator = read("src/scripts/generate_forward_remediation_scenarios_v1.py")
    assert "CHECK (NOT selection_uses_final_holdout)" in migration
    assert '"selection_uses_final_holdout": False' in generator
    assert '"parameter_mutation_allowed": False' in generator


def test_db_scheduler_owns_all_stage_executors() -> None:
    scheduler = read("src/scripts/run_db_job_scheduler_v1.py")
    migration = read("sql/analytics/082_forward_pass_progress_v1.sql")
    for executor in ("FORWARD_EVIDENCE_PIPELINE_V1", "FORWARD_PASS_PROGRESS_V1", "FORWARD_REMEDIATION_SCENARIOS_V1"):
        assert executor in scheduler
        assert executor in migration


def test_control_panel_shows_stage_and_real_progress_bars() -> None:
    resolver = read("src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py")
    renderer = read("src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py")
    driver = read("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js")
    assert "def _forward_pass_process" in resolver
    assert '("forward_pass_process", tuple(view_model.forward_pass_process))' in renderer
    assert 'node.content.column_code === "progress_pct"' in driver
    assert 'createElement("progress")' in driver


def test_i18n_has_russian_and_english_stage_resources() -> None:
    catalog = read("sql/presentation/077_forward_pass_progress_i18n_v1.sql")
    assert "Путь к Forward PASS" in catalog
    assert "Path to Forward PASS" in catalog
