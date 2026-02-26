from pathlib import Path
import json
from typing import Optional, Dict


class SnapshotRepository:
    def __init__(self, file_path: str = "data/snapshot.json"):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: Dict) -> None:
        payload = {
            "schema": 1,
            "data": snapshot,
        }

        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w") as f:
            json.dump(payload, f)

        tmp_path.replace(self.path)

    def load(self) -> Optional[Dict]:
        if not self.path.exists():
            return None
        with self.path.open("r") as f:
            payload = json.load(f)

            if "schema" not in payload:
                raise ValueError("Snapshot missing schema version")

            if payload["schema"] != 1:
                raise ValueError(f"Unsupported snapshot schema {payload['schema']}")

            return payload["data"]