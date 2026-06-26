from __future__ import annotations

from pathlib import Path

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


class PythonDiscovery:
    name = "PythonDiscovery"
    version = "PYTHON_DISCOVERY_PLUGIN_V1"

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        patterns = [
            "src/scripts/research/build_workflow_*.py",
            "src/scripts/research/serve_read_only_system_status_ui_v1.py",
            "src/marketcore/catalog/**/*.py",
        ]

        for pattern in patterns:
            for path in sorted(self.root.glob(pattern)):
                if "__pycache__" in path.parts:
                    continue
                if path.name == "__init__.py":
                    continue

                category = "SCRIPT"
                object_type = "PROCESS"

                if path.name.startswith("serve_"):
                    category = "SERVICE"
                    object_type = "PRESENTATION"
                elif "discovery" in path.parts:
                    category = "BUILDER"
                    object_type = "PROCESS"
                elif "writer" in path.parts:
                    category = "BUILDER"
                    object_type = "PROCESS"

                objects.append(
                    DiscoveredObject(
                        object_id=f"python:{path.as_posix()}",
                        object_name=path.name,
                        domain=context.domain,
                        category=category,
                        object_type=object_type,
                        schema_name=None,
                        warehouse_layer="PRESENTATION" if object_type == "PRESENTATION" else "LEGACY",
                        source_system="REPOSITORY",
                        source_type="DERIVED",
                        rows_count=None,
                        last_update=None,
                        discovery_source=self.name,
                        discovery_version=self.version,
                        payload={
                            "path": path.as_posix(),
                            "profile": context.profile,
                        },
                    )
                )

        return objects
