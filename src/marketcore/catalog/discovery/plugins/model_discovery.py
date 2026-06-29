from __future__ import annotations

from pathlib import Path

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


class ModelDiscovery:
    name = "ModelDiscovery"
    version = "MODEL_DISCOVERY_PLUGIN_V1"

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        patterns = ("src/**/*.py", "scripts/*.sh")
        keywords = (
            "model", "models", "classifier", "predict", "prediction",
            "regression", "bayes", "cluster", "ensemble", "optimizer",
            "xgboost", "lightgbm", "catboost", "lstm", "transformer",
            "neural", "ml", "ai",
        )

        for pattern in patterns:
            for path in sorted(self.root.glob(pattern)):
                if "__pycache__" in path.parts or not path.is_file():
                    continue

                name = path.name.lower()
                full = path.as_posix().lower()
                found = [k for k in keywords if k in name or k in full]
                if not found:
                    continue

                objects.append(
                    DiscoveredObject(
                        object_id=f"model:{path.as_posix()}",
                        object_name=path.name,
                        domain="MODELS",
                        category="MODEL",
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
                            "model_type": "UNKNOWN_MODEL_OR_MODEL_RELATED_ARTIFACT",
                            "keywords": found,
                            "approved_for_research": True,
                            "approved_for_shadow": False,
                            "approved_for_paper": False,
                            "approved_for_live": False,
                            "model_governance": "MODEL_GOVERNANCE_V1",
                        },
                    )
                )

        return objects
