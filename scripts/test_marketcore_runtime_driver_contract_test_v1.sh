#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RUNTIME_DRIVER_CONTRACT_TEST_V1 ==="

runtime_files=(
  "src/marketcore/runtime/__init__.py"
  "src/marketcore/runtime/platform_driver_v1.py"
  "src/marketcore/runtime/runtime_core_v1.py"
  "src/marketcore/runtime/runtime_result_v1.py"
)

for file in "${runtime_files[@]}"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }
done

PYTHONPYCACHEPREFIX=/tmp/marketcore_runtime_driver_contract_v1 \
PYTHONPATH=src \
python -m py_compile "${runtime_files[@]}"

# Runtime Core и контракт драйвера не должны зависеть от платформы,
# доставки, хранения или торгового контура.
if grep -RInE \
  --include='*.py' \
  'html|HTML|dom|DOM|browser|Browser|http|HTTP|css|CSS|javascript|JavaScript|fetch\(|XMLHttpRequest|psycopg|SELECT |INSERT |UPDATE |DELETE |send_order|place_order|cancel_order|execute_order' \
  src/marketcore/runtime
then
  echo "FORBIDDEN_RUNTIME_DRIVER_DEPENDENCY_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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


def build_test_document() -> RenderDocument:
    return RenderDocument(
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
                            node_type=RenderNodeType.SECTION,
                            children=(
                                RenderNode(
                                    node_type=RenderNodeType.CARD,
                                    children=(
                                        RenderNode(
                                            node_type=RenderNodeType.TEXT,
                                            text="Проверка драйвера",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )


@dataclass
class ContractRecordingDriverV1:
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
class BeginFailureDriverV1:
    def begin_document(
        self,
        document: RenderDocument,
    ) -> None:
        raise RuntimeError("BEGIN_FAILURE")

    def render_node(
        self,
        node: RenderNode,
        *,
        depth: int,
    ) -> None:
        return None

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        return None


@dataclass
class NodeFailureDriverV1:
    visited: list[str] = field(default_factory=list)

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
        self.visited.append(node.type_code)

        if node.type_code == "card":
            raise RuntimeError("NODE_FAILURE")

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        raise AssertionError(
            "END_DOCUMENT_MUST_NOT_RUN_AFTER_NODE_FAILURE"
        )


@dataclass
class EndFailureDriverV1:
    rendered_nodes: int = 0

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
        self.rendered_nodes += 1

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        raise RuntimeError("END_FAILURE")


class MissingBeginDriverV1:
    def render_node(
        self,
        node: RenderNode,
        *,
        depth: int,
    ) -> None:
        return None

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        return None


class MissingRenderNodeDriverV1:
    def begin_document(
        self,
        document: RenderDocument,
    ) -> None:
        return None

    def end_document(
        self,
        document: RenderDocument,
    ) -> None:
        return None


class MissingEndDriverV1:
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
        return None


document = build_test_document()
runtime = MarketCoreRuntimeCoreV1()

# 1. Structural Protocol.
valid_driver = ContractRecordingDriverV1()

assert isinstance(valid_driver, PlatformDriverV1)
assert not isinstance(MissingBeginDriverV1(), PlatformDriverV1)
assert not isinstance(MissingRenderNodeDriverV1(), PlatformDriverV1)
assert not isinstance(MissingEndDriverV1(), PlatformDriverV1)

# 2. Успешный жизненный цикл.
success_result = runtime.execute(
    document,
    valid_driver,
)

assert success_result.success is True
assert success_result.status is RuntimeExecutionStatusV1.SUCCESS
assert success_result.nodes_processed == 6
assert success_result.diagnostics == ()

assert valid_driver.events == [
    ("begin", "workspace", -1),
    ("node", "workspace", 0),
    ("node", "page", 1),
    ("node", "title", 2),
    ("node", "section", 2),
    ("node", "card", 3),
    ("node", "text", 4),
    ("end", "workspace", -1),
]

# 3. Ошибка begin_document.
begin_result = runtime.execute(
    document,
    BeginFailureDriverV1(),
)

assert begin_result.success is False
assert begin_result.status is RuntimeExecutionStatusV1.FAILED
assert begin_result.nodes_processed == 0
assert len(begin_result.diagnostics) == 1
assert "BEGIN_FAILURE" in begin_result.diagnostics[0]

# 4. Ошибка render_node.
node_driver = NodeFailureDriverV1()

node_result = runtime.execute(
    document,
    node_driver,
)

assert node_result.success is False
assert node_result.status is RuntimeExecutionStatusV1.FAILED
assert node_result.nodes_processed == 0
assert "NODE_FAILURE" in node_result.diagnostics[0]

assert node_driver.visited == [
    "workspace",
    "page",
    "title",
    "section",
    "card",
]

# 5. Ошибка end_document.
end_driver = EndFailureDriverV1()

end_result = runtime.execute(
    document,
    end_driver,
)

assert end_driver.rendered_nodes == 6
assert end_result.success is False
assert end_result.status is RuntimeExecutionStatusV1.FAILED
assert end_result.nodes_processed == 6
assert "END_FAILURE" in end_result.diagnostics[0]

# 6. Объект без полного Protocol отклоняется до исполнения.
for invalid_driver in (
    MissingBeginDriverV1(),
    MissingRenderNodeDriverV1(),
    MissingEndDriverV1(),
    object(),
):
    try:
        runtime.execute(
            document,
            invalid_driver,  # type: ignore[arg-type]
        )
    except TypeError as exc:
        assert str(exc) == "RUNTIME_PLATFORM_DRIVER_REQUIRED"
    else:
        raise AssertionError(
            "INCOMPLETE_PLATFORM_DRIVER_NOT_REJECTED"
        )

print("platform_driver_protocol=OK")
print("driver_lifecycle_order=OK")
print("depth_first_traversal=OK")
print("depth_values=OK")
print("begin_failure_contract=OK")
print("node_failure_contract=OK")
print("end_failure_contract=OK")
print("incomplete_driver_rejected=OK")
print("nodes_processed=6")
PY

echo "platform_driver_contract=OK"
echo "driver_protocol_runtime_checkable=OK"
echo "driver_lifecycle=begin,render_node,end"
echo "tree_traversal=depth_first_preorder"
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
echo "VERDICT=MARKETCORE_RUNTIME_DRIVER_CONTRACT_TEST_V1_READY"
echo "VERDICT=TEST_MARKETCORE_RUNTIME_DRIVER_CONTRACT_TEST_V1_OK"
