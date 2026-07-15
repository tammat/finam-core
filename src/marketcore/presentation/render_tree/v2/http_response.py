from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.render_tree.v2.model import RenderDocumentV2
from marketcore.presentation.render_tree.v2.serialization import render_document_v2_to_json
from marketcore.presentation.render_tree.v2.validation import validate_render_document_v2


RENDER_TREE_V2_MEDIA_TYPE = (
    "application/vnd.marketcore.render-tree+json; charset=utf-8"
)


@dataclass(frozen=True, slots=True)
class RenderTreeHttpResponseV2:
    status_code: int
    content_type: str
    body: bytes


def build_render_tree_http_response_v2(
    document: RenderDocumentV2,
) -> RenderTreeHttpResponseV2:
    validate_render_document_v2(document)
    return RenderTreeHttpResponseV2(
        status_code=200,
        content_type=RENDER_TREE_V2_MEDIA_TYPE,
        body=render_document_v2_to_json(document).encode("utf-8"),
    )
