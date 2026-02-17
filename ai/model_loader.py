# Комментарии:
# Загружает активную модель из Postgres registry.
# Возвращает: model, threshold, feature list.
# Не зависит от стратегии и execution.

import json
import joblib
from pathlib import Path

from storage.postgres import PostgresStorage


class ModelLoader:

    def __init__(self, model_name="baseline_logreg"):
        self.model_name = model_name
        self.storage = PostgresStorage()

    def load_latest(self):
        with self.storage.conn.cursor() as cur:
            cur.execute(
                """
                SELECT version, dataset_path, features, threshold
                FROM model_registry
                WHERE model_name = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (self.model_name,),
            )

            row = cur.fetchone()

        if not row:
            raise ValueError(f"No model found for {self.model_name}")

        version, dataset_path, features_json, threshold = row

        artifact_path = Path("data/models/baseline_logreg.joblib")
        if not artifact_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {artifact_path}")

        artifact = joblib.load(artifact_path)

        return {
            "model": artifact["model"],
            "threshold": threshold,
            "features": artifact["features"],
            "version": version,
        }