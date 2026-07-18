from pathlib import Path


def test_every_operator_command_has_a_process_mapping() -> None:
    sql = Path("sql/marketcore_action/103_unified_command_process_v1.sql").read_text()
    for process_type in ("PAPER_OBSERVATION", "OPERATOR_DECISION", "RESEARCH_UNIVERSE"):
        assert process_type in sql
    assert "NEW.process_id := NEW.request_id::uuid" in sql
    assert "COMMAND_REQUESTED" in sql


def test_inline_commands_can_be_run_by_request_kind() -> None:
    source = Path("src/marketcore/action/command_worker_v2.py").read_text()
    assert '"RESEARCH_UNIVERSE_INCLUDE"' in source
    assert 'request_kind not in inline_commands' in source
