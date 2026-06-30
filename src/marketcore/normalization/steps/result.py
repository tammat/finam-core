from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StepResult:
    success: bool = True

    duration_ms: int = 0

    rows_processed: int = 0
    rows_rejected: int = 0

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
