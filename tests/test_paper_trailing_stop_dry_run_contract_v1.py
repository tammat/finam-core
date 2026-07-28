from pathlib import Path


def test_paper_trailing_dry_run_persists_virtual_stop_without_broker_replace():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "finam_core"
        / "pipelines"
        / "paper_pipeline.py"
    ).read_text(encoding="utf-8")
    method = source.split(
        "    def _evaluate_trailing_order_manager(", 1
    )[1].split(
        "    def _log_position_order_state_if_changed(", 1
    )[0]
    dry_run_branch = method.split("            else:", 1)[1]

    assert "PIPE_PAPER_TRAILING_STOP_APPLIED" in dry_run_branch
    assert "_handle_trailing_replace_stop_decision" not in dry_run_branch


def test_position_lifecycle_service_uses_the_same_virtual_paper_stop_contract():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "finam_core"
        / "execution"
        / "position_lifecycle_service.py"
    ).read_text(encoding="utf-8")
    start = source.index("    def _evaluate_trailing_order_manager(")
    end = source.index("\n    def ", start + 10)
    method = source[start:end]

    assert "PIPE_PAPER_TRAILING_STOP_APPLIED" in method
    assert "p._handle_trailing_replace_stop_decision(decision)" not in method
