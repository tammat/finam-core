from __future__ import annotations

from typing import Final

REGISTRY_SCHEMA: Final[str] = "warehouse"
DEFAULT_PAGE_SIZE: Final[int] = 100
DEFAULT_STATUS: Final[str] = "DISCOVERED"
DEFAULT_MATURITY: Final[str] = "RESEARCH"
DEFAULT_PAYLOAD_SQL: Final[str] = "'{}'::jsonb"

REGISTRY_DATE_FIELDS: Final[tuple[str, ...]] = (
    "created_at",
    "updated_at",
)
