from __future__ import annotations

from marketcore.presentation.render_tree.v2.http_response import (
    RenderTreeHttpResponseV2,
    build_render_tree_http_response_v2,
)
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import (
    DomainProducerCodeV2,
    build_domain_document_v2,
)


def domain_render_tree_http_v2(
    producer_code: DomainProducerCodeV2 | str,
    *,
    timezone_code: str | None = None,
) -> RenderTreeHttpResponseV2:
    document = build_domain_document_v2(
        producer_code,
        timezone_code=timezone_code,
    )
    return build_render_tree_http_response_v2(document)
