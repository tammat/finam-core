from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RenderNode:
    node_type: str
    props: dict[str, Any] = field(default_factory=dict)
    children: tuple["RenderNode", ...] = ()
    text: str = ""
