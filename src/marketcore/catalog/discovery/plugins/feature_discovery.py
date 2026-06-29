from __future__ import annotations

from pathlib import Path

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


class FeatureDiscovery:
    name = "FeatureDiscovery"
    version = "FEATURE_DISCOVERY_PLUGIN_V1"

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        patterns = (
            "src/**/*.py",
            "scripts/*.sh",
        )

        keywords = (
            "feature",
            "indicator",
            "atr",
            "rsi",
            "volatility",
            "volume",
            "liquidity",
            "correlation",
            "regime",
            "momentum",
            "trend",
        )

        for pattern in patterns:
            for path in sorted(self.root.glob(pattern)):
                if "__pycache__" in path.parts:
                    continue
                if not path.is_file():
                    continue

                name = path.name.lower()
                full = path.as_posix().lower()

                if not any(k in name or k in full for k in keywords):
                    continue

                if path.suffix == ".py":
                    category = "FEATURE"
                elif path.suffix == ".sh":
                    category = "SCRIPT"
                else:
                    category = "FEATURE"

                objects.append(
                    DiscoveredObject(
                        object_id=f"feature:{path.as_posix()}",
                        object_name=path.name,
                        domain="FEATURES",
                        category=category,
                        object_type="KNOWLEDGE",
                        schema_name=None,
                        warehouse_layer="LEGACY",
                        source_system="REPOSITORY",
                        source_type="DERIVED",
                        rows_count=None,
                        last_update=None,
                        discovery_source=self.name,
                        discovery_version=self.version,
                        payload={
                            "path": path.as_posix(),
                            "profile": context.profile,
                            "keywords": [k for k in keywords if k in name or k in full],
                            "approved_for_research": True,
                            "approved_for_shadow": False,
                            "approved_for_paper": False,
                            "approved_for_live": False,
                        },
                    )
                )

        return objects
