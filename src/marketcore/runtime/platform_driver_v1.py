from __future__ import annotations

from typing import Protocol, runtime_checkable

from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode


@runtime_checkable
class PlatformDriverV1(Protocol):
    """Контракт платформенного драйвера MarketCore Runtime V1."""

    def begin_document(
        self,
        document: RenderDocument,
    ) -> None:
        """Начинает обработку документа."""

    def render_node(
        self,
        node: RenderNode,
        *,
        depth: int,
    ) -> None:
        """Обрабатывает один узел RenderTree."""

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        """Завершает обработку документа."""
