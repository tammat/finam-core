from pathlib import Path


STATUS_SCRIPT = Path(
    "scripts/research/"
    "show_ngu6_mean_reversion_forward_status_v1.py"
)


def test_status_command_exists():
    assert STATUS_SCRIPT.is_file()


def test_status_command_is_read_only_by_construction():
    source = STATUS_SCRIPT.read_text().lower()

    forbidden = (
        "insert into",
        "update ",
        "delete from",
        "create table",
        "alter table",
        "drop table",
        "truncate ",
    )

    for token in forbidden:
        assert token not in source


def test_status_connection_is_readonly():
    source = STATUS_SCRIPT.read_text()

    assert "conn.set_session(readonly=True)" in source


def test_status_checks_safety_and_lineage():
    source = STATUS_SCRIPT.read_text()

    required = (
        "unsafe_count",
        "lineage_mismatch",
        "UNSAFE_FORWARD_OBSERVATION",
        "FORWARD_LINEAGE_MISMATCH",
        "DATABASE_WRITE=NO",
        "paper_allowed=0",
        "micro_live_allowed=0",
        "NGU6_FORWARD_STATUS_READONLY_OK",
    )

    for token in required:
        assert token in source


def test_profit_factor_is_not_zero_when_undefined():
    source = STATUS_SCRIPT.read_text()

    assert "profit_factor = None" in source
    assert "'NONE'" in source
