from pathlib import Path


def test_designer_layout_copy_is_db_driven() -> None:
    migration = Path(
        "sql/presentation/166_control_center_designer_layout_i18n_v1.sql"
    ).read_text(encoding="utf-8")
    for key in (
        "control.view.group.process.description",
        "control.view.group.funnel.description",
        "control.view.group.execution.description",
        "control.view.group.methodology.description",
        "control.view.group.count",
    ):
        assert key in migration
    assert "ограничений" in migration
