from __future__ import annotations

from enum import Enum


class StepTag(str, Enum):
    RESOLUTION = "RESOLUTION"
    BUILD = "BUILD"
    QUALITY = "QUALITY"
    LINEAGE = "LINEAGE"
    PERSIST = "PERSIST"
    AUDIT = "AUDIT"
