from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.serialization_v1 import (
    RenderTreeSerializerV1,
)


@dataclass(frozen=True, slots=True)
class RenderTreeHttpResponseV1:
    """Платформонезависимое содержимое HTTP-ответа RenderTree."""

    status_code: int
    content_type: str
    body: bytes


def build_render_tree_http_response_v1(
    document: RenderDocument,
) -> RenderTreeHttpResponseV1:
    if not isinstance(document, RenderDocument):
        raise TypeError("RENDER_DOCUMENT_REQUIRED")

    json_text = RenderTreeSerializerV1.to_json(document)

    return RenderTreeHttpResponseV1(
        status_code=200,
        content_type="application/json; charset=utf-8",
        body=json_text.encode("utf-8"),
    )
