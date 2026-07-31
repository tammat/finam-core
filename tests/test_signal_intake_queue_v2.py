from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_signal_queue_is_db_driven_and_safe():
    sql = (ROOT / "sql/analytics/131_signal_intake_queue_v2.sql").read_text()
    worker = (ROOT / "src/scripts/process_signal_intake_queue_v2.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "AFTER INSERT ON public.signals" in sql
    assert "ON CONFLICT DO NOTHING" in sql
    assert "SIGNAL_INTAKE_QUEUE_V2" in scheduler
    assert "FOR UPDATE SKIP LOCKED" in worker
    assert "priority,next_attempt_at,enqueued_at" in worker
    assert "SIGNAL_LIFECYCLE_TIMEOUT_SECONDS" in worker
    assert "SET status='RISK_REJECTED'" in worker
    assert "signal_lifecycle_timeout" in worker
    assert "reconciled_fills" in worker
    assert "EXISTS (" in worker
    assert "public.signal_fills" in worker
    assert "SET status='FILLED'" in worker
    assert "superseded_after_pipeline_restart" in worker
    assert "SUPERSEDED_BY_NEWER_TERMINAL_SIGNAL" in worker
    assert "regime_bar_ts" in worker
    assert 'print("execution_changed=0")' in worker
    assert 'print("live_allowed=0")' in worker


def test_signal_queue_does_not_send_orders():
    worker = (ROOT / "src/scripts/process_signal_intake_queue_v2.py").read_text()
    forbidden = ("create_order(", "submit_order(", "runtime_allowed=true")
    assert all(token not in worker for token in forbidden)
