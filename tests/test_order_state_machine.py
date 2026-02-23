from execution.order_manager import OrderManager
from execution.order_events import FillEvent
from execution.order import OrderStatus


def main():
    om = OrderManager()

    # create + accept
    order = om.create_order("1", "NG", "BUY", 10, 100)
    om.accept_order("1")
    assert order.status == OrderStatus.ACCEPTED

    # partial fill
    om.on_fill(FillEvent("f1", "1", 4))
    assert order.status == OrderStatus.PARTIAL
    assert order.filled_qty == 4

    # final fill
    om.on_fill(FillEvent("f2", "1", 6))
    assert order.status == OrderStatus.FILLED
    assert order.filled_qty == 10

    # duplicate fill
    try:
        om.on_fill(FillEvent("f2", "1", 1))
        raise RuntimeError("expected duplicate error")
    except RuntimeError as e:
        assert "DUPLICATE_FILL" in str(e)

    # invalid transition
    try:
        om.cancel_order("1")
        raise RuntimeError("expected invalid transition")
    except RuntimeError as e:
        assert "INVALID_STATE_TRANSITION" in str(e)

    print("ok: order state machine works")


if __name__ == "__main__":
    raise SystemExit(main())