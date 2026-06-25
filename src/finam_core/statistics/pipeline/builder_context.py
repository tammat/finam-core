# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BuilderContext:
    builder_name: str
    fact_domain: str
    fact_type: str
    source_table: str
    target_table: str
    calculation_version: str
    payload: dict[str, Any] = field(default_factory=dict)
