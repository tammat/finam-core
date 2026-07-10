from __future__ import annotations

from marketcore.presentation.adapters.web.render_document_to_html_v1 import RenderDocumentToHtmlV1
from marketcore.presentation.workspace_v2.presenter.home_v2_presenter import HomeV2Presenter
from marketcore.presentation.workspace_v2.renderer.home_v2_renderer import render_home_v2


def render_workspace_v2_home_page_v2() -> str:
    vm = HomeV2Presenter().load()
    document = render_home_v2(vm)
    return RenderDocumentToHtmlV1.render(document)


if __name__ == "__main__":
    print(render_workspace_v2_home_page_v2())
