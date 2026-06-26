from __future__ import annotations

from pathlib import Path

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


class SystemdDiscovery:
    name = "SystemdDiscovery"
    version = "SYSTEMD_DISCOVERY_PLUGIN_V1"

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        for pattern in ("systemd/*.service", "systemd/*.timer", "systemd/*.env"):
            for path in sorted(self.root.glob(pattern)):
                if not path.is_file():
                    continue

                suffix = path.suffix.lower()
                if suffix == ".service":
                    category = "SERVICE"
                elif suffix == ".timer":
                    category = "SERVICE"
                elif suffix == ".env":
                    category = "SCRIPT"
                else:
                    category = "SCRIPT"

                objects.append(
                    DiscoveredObject(
                        object_id=f"systemd:{path.as_posix()}",
                        object_name=path.name,
                        domain=context.domain,
                        category=category,
                        object_type="PROCESS",
                        schema_name=None,
                        warehouse_layer="PRESENTATION" if "readonly" in path.name or "ui" in path.name else "LEGACY",
                        source_system="REPOSITORY",
                        source_type="DERIVED",
                        rows_count=None,
                        last_update=None,
                        discovery_source=self.name,
                        discovery_version=self.version,
                        payload={
                            "path": path.as_posix(),
                            "suffix": suffix,
                            "profile": context.profile,
                        },
                    )
                )

        return objects
