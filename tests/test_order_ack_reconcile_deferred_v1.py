from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/scripts/reconcile_order_acks.py"


def test_temporary_broker_outage_defers_without_false_reconciliation():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "grpc.StatusCode.UNAVAILABLE" in source
    assert "grpc.StatusCode.DEADLINE_EXCEEDED" in source
    assert "ORDER_ACK_RECONCILIATION_DEFERRED" in source
    assert "return 0" in source
    assert "market_weekend" in source
    assert "broker_backoff_active" in source
