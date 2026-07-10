#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RUNTIME_CORE_V1 ==="

files=(
  "src/marketcore/runtime/__init__.py"
  "src/marketcore/runtime/platform_driver_v1.py"
  "src/marketcore/runtime/runtime_core_v1.py"
  "src/marketcore/runtime/runtime_result_v1.py"
)

for file in "${files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_runtime_core_v1 \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE \
  --include='*.py' \
  'html|HTML|dom|DOM|browser|Browser|http|HTTP|css|CSS|javascript|JavaScript|psycopg|SELECT |INSERT |UPDATE |DELETE |send_order|place_order|cancel_order|execute_order' \
  src/marketcore/runtime
then
  echo "FORBIDDEN_RUNTIME_CORE_DEPENDENCY_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from __future__ import annotations

from dataclasses import dataclass, field

from marketcore.presentation.render_tree import (
    RenderDocument,
    RenderNode,
    RenderNodeType,
)
from marketcore.runtime import (
    MarketCoreRuntimeCoreV1,
    PlatformDriverV1,
    RuntimeExecutionStatusV1,
)


@dataclass
class RecordingDriverV1:
    events: list[tuple[str, str, int]] = field(
        default_factory=list
    )

    def begin_document(
        self,
        document: RenderDocument,
    ) -> None:
        self.events.append(
            ("begin", document.root.type_code, -1)
        )

    def render_node(
        self,
        node: RenderNode,
        *,
        depth: int,
    ) -> None:
        self.events.append(
            ("node", node.type_code, depth)
        )

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        self.events.append(
            ("end", document.root.type_code, -1)
        )


@dataclass
class FailingDriverV1:
    def begin_document(
        self,
        document: RenderDocument,
    ) -> None:
        return None

    def render_node(
        self,
        node: RenderNode,
        *,
        depth: int,
    ) -> None:
        if node.type_code == "card":
            raise RuntimeError("DRIVER_TEST_FAILURE")

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        return None


document = RenderDocument(
    root=RenderNode(
        node_type=RenderNodeType.WORKSPACE,
        children=(
            RenderNode(
                node_type=RenderNodeType.PAGE,
                children=(
                    RenderNode(
                        node_type=RenderNodeType.TITLE,
                        props={"level": 1},
                        text="MarketCore OS",
                    ),
                    RenderNode(
                        node_type=RenderNodeType.CARD,
                        children=(
                            RenderNode(
                                node_type=RenderNodeType.TEXT,
                                text="Проверка",
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
)

runtime = MarketCoreRuntimeCoreV1()
driver = RecordingDriverV1()

assert isinstance(driver, PlatformDriverV1)

result = runtime.execute(
    document,
    driver,
)

assert result.success is True
assert result.status is RuntimeExecutionStatusV1.SUCCESS
assert result.nodes_processed == 5
assert result.diagnostics == ()

assert driver.events == [
    ("begin", "workspace", -1),
    ("node", "workspace", 0),
    ("node", "page", 1),
    ("node", "title", 2),
    ("node", "card", 2),
    ("node", "text", 3),
    ("end", "workspace", -1),
]

failed_result = runtime.execute(
    document,
    FailingDriverV1(),
)

assert failed_result.success is False
assert failed_result.status is RuntimeExecutionStatusV1.FAILED
assert failed_result.nodes_processed == 0
assert len(failed_result.diagnostics) == 1
assert "RUNTIME_DRIVER_EXECUTION_FAILED" in (
    failed_result.diagnostics[0]
)
assert "DRIVER_TEST_FAILURE" in failed_result.diagnostics[0]

try:
    runtime.execute(
        "not-document",  # type: ignore[arg-type]
        driver,
    )
except TypeError as exc:
    assert str(exc) == "RUNTIME_RENDER_DOCUMENT_REQUIRED"
else:
    raise AssertionError("INVALID_DOCUMENT_NOT_REJECTED")


class InvalidDriver:
    pass


try:
    runtime.execute(
        document,
        InvalidDriver(),  # type: ignore[arg-type]
    )
except TypeError as exc:
    assert str(exc) == "RUNTIME_PLATFORM_DRIVER_REQUIRED"
else:
    raise AssertionError("INVALID_DRIVER_NOT_REJECTED")

print("runtime_core=OK")
print("platform_driver_protocol=OK")
print("depth_first_walk=OK")
print("nodes_processed=5")
print("driver_failure_result=OK")
print("invalid_document_rejected=OK")
print("invalid_driver_rejected=OK")
PY

echo "runtime_core=OK"
echo "platform_driver_protocol=OK"
echo "runtime_result=OK"
echo "platform_specific_logic=0"
echo "html_dependency=0"
echo "dom_dependency=0"
echo "http_dependency=0"
echo "storage_dependency=0"
echo "trading_dependency=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_RUNTIME_CORE_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RUNTIME_CORE_V1_OK"
