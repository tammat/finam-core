from finam_core.strategy.exit_engine import ExitStateMachine


def test_failed_exit_is_released_for_immediate_retry() -> None:
    machine = ExitStateMachine(ttl_sec=30.0)
    machine.on_position("SBER@MISX", 1.0)

    allowed, _ = machine.allow_request("SBER@MISX", "SELL", 1.0, "time_exit")
    assert allowed is True

    duplicate_allowed, duplicate_reason = machine.allow_request(
        "SBER@MISX", "SELL", 1.0, "time_exit"
    )
    assert duplicate_allowed is False
    assert duplicate_reason == "duplicate_exit_request_active"

    machine.on_failed("SBER@MISX")

    retry_allowed, retry_reason = machine.allow_request(
        "SBER@MISX", "SELL", 1.0, "time_exit"
    )
    assert retry_allowed is True
    assert retry_reason == "exit_request_allowed"
