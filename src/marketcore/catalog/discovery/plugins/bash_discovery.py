from __future__ import annotations

from pathlib import Path

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


class BashDiscovery:
    name = "BashDiscovery"
    version = "BASH_DISCOVERY_PLUGIN_V1"

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        patterns = (
            "scripts/test_workflow_*.sh",
            "scripts/test_catalog_*.sh",
            "scripts/setup_systemd_read_only_system_status_ui_v1.sh",
            "scripts/test_read_only_system_status_ui_v1.sh",
            "scripts/test_readonly_ui_db_grants_v1.sh",
        )

        for pattern in patterns:
            for path in sorted(self.root.glob(pattern)):
                if not path.is_file():
                    continue

                category = "SCRIPT"
                object_type = "PROCESS"
                warehouse_layer = "LEGACY"

                if path.name.startswith("test_"):
                    purpose_kind = "test"
                elif path.name.startswith("setup_"):
                    purpose_kind = "setup"
                else:
                    purpose_kind = "script"

                objects.append(
                    DiscoveredObject(
                        object_id=f"bash:{path.as_posix()}",
                        object_name=path.name,
                        domain=context.domain,
                        category=category,
                        object_type=object_type,
                        schema_name=None,
                        warehouse_layer=warehouse_layer,
                        source_system="REPOSITORY",
                        source_type="DERIVED",
                        rows_count=None,
                        last_update=None,
                        discovery_source=self.name,
                        discovery_version=self.version,
                        payload={
                            "path": path.as_posix(),
                            "purpose_kind": purpose_kind,
                            "profile": context.profile,
                        },
                    )
                )

        return objects
