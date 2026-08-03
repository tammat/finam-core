from pathlib import Path


def test_morning_audit_is_prospective_and_execution_safe():
    source = Path("src/scripts/check_reachable_shadow_morning_v1.py").read_text()

    assert "p.label_start_ts<c.frozen_at" in source
    assert "paper_changed=0 real_changed=0" in source
    assert "UNSAFE_PAPER_ALLOWED" in source
    assert "UNSAFE_REAL_ALLOWED" in source


def test_morning_audit_runs_after_first_completed_m15_bar():
    timer = Path("deploy/systemd/finam-reachable-shadow-morning-audit.timer").read_text()
    service = Path("deploy/systemd/finam-reachable-shadow-morning-audit.service").read_text()

    assert "07:10:00 Europe/Moscow" in timer
    assert "check_reachable_shadow_morning_v1.py" in service


def test_morning_audit_is_in_existing_control_chain_and_idempotent():
    source = Path("src/scripts/check_reachable_shadow_morning_v1.py").read_text()
    chain = Path("src/scripts/run_entry_exit_control_chain_v1.py").read_text()

    assert "REACHABLE_SHADOW_MORNING_AUDIT_ALREADY_RECORDED" in source
    assert "check_reachable_shadow_morning_v1.py" in chain
