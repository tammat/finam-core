# tests/test_event_bus_contract.py
import pytest

from finam_core.events.event_bus import EventBus


def test_event_bus_subscribe_publish_contract():
    bus = EventBus()

    got = []

    def handler(ev: dict):
        got.append(ev)

    # contract: subscribe(event_type, handler)
    bus.subscribe("QUOTE", handler)

    ev = {"type": "QUOTE", "symbol": "TEST@MISX", "last": 123.45}
    # contract: publish(event) (one argument)
    bus.publish(ev)

    assert got == [ev]


def test_event_bus_publish_unknown_type_no_crash():
    bus = EventBus()
    # no subscribers for this type -> should not crash
    bus.publish({"type": "UNKNOWN", "x": 1})