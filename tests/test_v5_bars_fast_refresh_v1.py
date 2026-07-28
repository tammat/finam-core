from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fast_refresh_is_exact_research_only_target_set() -> None:
    unit = (ROOT / "deploy/systemd/finam-v5-bars-fast.service").read_text()
    assert "Type=oneshot" in unit
    assert "--once --targets" in unit
    for target in (
        "BRQ6@RTSX=M1", "NGQ6@RTSX=M1", "SBER@MISX=M1",
        "GAZP@MISX=M1", "LKOH@MISX=M1", "NVTK@MISX=M5",
        "VTBR@MISX=M5",
    ):
        assert target in unit
    assert "EXECUTION_ENABLED=1" not in unit
    assert "REAL_TRADING_ENABLED=1" not in unit


def test_fast_refresh_timer_cannot_overlap_its_oneshot_service() -> None:
    timer = (ROOT / "deploy/systemd/finam-v5-bars-fast.timer").read_text()
    assert "OnUnitInactiveSec=60" in timer
    assert "AccuracySec=5s" in timer
    assert "Persistent=true" in timer
