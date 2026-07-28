from pathlib import Path


def test_idle_checks_do_not_move_completed_cycle_clock() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "scripts"
        / "build_edge_discovery_autorun_v1.py"
    ).read_text(encoding="utf-8")

    assert "AND status='FINISHED'" in source
    assert "status IN ('FINISHED','IDLE')" not in source
