from typing import List, Any


class SignalRouter:
    """
    Responsible for selecting final signal from a strategy stack.
    """

    def __init__(self, policy: str = "first") -> None:
        self.policy = policy

    def route(self, signals: List[Any]) -> Any:
        if not signals:
            return None

        if self.policy == "first":
            return signals[0]

        if self.policy == "last":
            return signals[-1]

        if self.policy == "priority":
            # expects signal.priority attribute
            return sorted(
                signals,
                key=lambda s: getattr(s, "priority", 0),
                reverse=True
            )[0]

        # default fallback
        return signals[0]