# Комментарии:
# EventBus — простая FIFO очередь событий.
# Никакого pub/sub.
# Engine сам решает, как маршрутизировать события.

from collections import deque


class EventBus:

    def __init__(self):
        self._queue = deque()

    def publish(self, event):
        self._queue.append(event)

    def has_events(self):
        return len(self._queue) > 0

    def get(self):
        return self._queue.popleft()