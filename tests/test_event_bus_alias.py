#tests/test_event_bus_alias.py
# tests/test_event_bus_alias.py
# Русский коммент: фиксируем контракт — EventBus единый.

def test_event_bus_alias_same_class():
    from finam_core.events.event_bus import EventBus as EventsBus
    from finam_core.core.event_bus import EventBus as CoreBus

    assert CoreBus is EventsBus, "core.event_bus.EventBus must be alias to events.event_bus.EventBus"