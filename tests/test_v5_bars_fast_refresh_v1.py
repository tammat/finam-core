from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fast_refresh_is_exact_research_only_target_set() -> None:
    unit = (ROOT / "deploy/systemd/finam-v5-bars-fast.service").read_text()
    assert "Type=oneshot" in unit
    assert "--once --targets" in unit
    frozen_v5_targets = (
        "BRQ6@RTSX=M1",
        "SBER@MISX=M1",
        "GDU6@RTSX=M1",
        "CNYRUBF@RTSX=M1",
    )
    for target in frozen_v5_targets:
        assert target in unit
    targets_value = unit.split("--targets ", 1)[1].split(" ", 1)[0]
    assert tuple(targets_value.split(",")) == frozen_v5_targets
    assert "EXECUTION_ENABLED=1" not in unit
    assert "REAL_TRADING_ENABLED=1" not in unit


def test_fast_refresh_timer_cannot_overlap_its_oneshot_service() -> None:
    timer = (ROOT / "deploy/systemd/finam-v5-bars-fast.timer").read_text()
    assert "OnUnitInactiveSec=60" in timer
    assert "AccuracySec=5s" in timer
    assert "Persistent=true" in timer
