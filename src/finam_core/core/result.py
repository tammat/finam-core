from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineResult:
    status: str
    signal: Optional[object] = None
    order: Optional[object] = None