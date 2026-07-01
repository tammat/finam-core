from __future__ import annotations

from marketcore.presentation.viewmodels.metadata_center_vm import (
    MetadataCenterVM,
    build_default_metadata_center_vm,
)


class MetadataCenterService:
    def load(self) -> MetadataCenterVM:
        return build_default_metadata_center_vm()
