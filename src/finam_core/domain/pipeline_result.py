from dataclasses import dataclass
from typing import Optional
from finam_core.domain.order_execution import OrderExecution


@dataclass(frozen=True)
class PipelineResult:
    status: str
    order: Optional[OrderExecution] = None