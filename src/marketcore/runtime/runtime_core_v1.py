from __future__ import annotations

from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.runtime.platform_driver_v1 import PlatformDriverV1
from marketcore.runtime.runtime_result_v1 import (
    RuntimeExecutionResultV1,
    RuntimeExecutionStatusV1,
)


class MarketCoreRuntimeCoreV1:
    """Минимальное ядро исполнения платформонезависимого RenderTree."""

    def execute(
        self,
        document: RenderDocument,
        driver: PlatformDriverV1,
    ) -> RuntimeExecutionResultV1:
        if not isinstance(document, RenderDocument):
            raise TypeError("RUNTIME_RENDER_DOCUMENT_REQUIRED")

        if not isinstance(driver, PlatformDriverV1):
            raise TypeError("RUNTIME_PLATFORM_DRIVER_REQUIRED")

        nodes_processed = 0

        try:
            driver.begin_document(document)

            nodes_processed = self._walk(
                document.root,
                driver=driver,
                depth=0,
            )

            driver.end_document(document)

        except Exception as exc:
            return RuntimeExecutionResultV1(
                status=RuntimeExecutionStatusV1.FAILED,
                nodes_processed=nodes_processed,
                diagnostics=(
                    "RUNTIME_DRIVER_EXECUTION_FAILED:"
                    f"{type(exc).__name__}:{exc}",
                ),
            )

        return RuntimeExecutionResultV1(
            status=RuntimeExecutionStatusV1.SUCCESS,
            nodes_processed=nodes_processed,
        )

    def _walk(
        self,
        node: RenderNode,
        *,
        driver: PlatformDriverV1,
        depth: int,
    ) -> int:
        if not isinstance(node, RenderNode):
            raise TypeError("RUNTIME_RENDER_NODE_REQUIRED")

        driver.render_node(
            node,
            depth=depth,
        )

        nodes_processed = 1

        for child in node.children:
            nodes_processed += self._walk(
                child,
                driver=driver,
                depth=depth + 1,
            )

        return nodes_processed
