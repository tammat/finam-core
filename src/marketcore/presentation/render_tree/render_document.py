from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.render_tree.render_node import RenderNode


@dataclass(frozen=True, slots=True)
class RenderDocument:
    root: RenderNode
