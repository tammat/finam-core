from pathlib import Path


def test_active_trailing_is_scoped_to_todays_paper_symbols() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py"
    ).read_text(encoding="utf-8")
    assert "current_fill.created_at >= date_trunc('day',now())" in source
    assert "current_fill.symbol=position_lifecycle_state.symbol" in source
