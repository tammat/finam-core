import json
import os
from datetime import datetime,timezone


class FillJournal:

    def __init__(self, path="storage/fill_wal.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def append(self, fill: dict):
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "fill": fill,
        }

        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def read_all(self):
        if not os.path.exists(self.path):
            return []

        records = []
        with open(self.path, "r") as f:
            for line in f:
                records.append(json.loads(line))
        return records

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)