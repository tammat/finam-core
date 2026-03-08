import os
from pathlib import Path

from finam_core.storage.postgres import PostgresStorage
from research.dataset_builder import DatasetBuilder


def main():
    storage = PostgresStorage()
    builder = DatasetBuilder(storage)

    # Русский коммент: символ из окружения, дефолт — NGH6@RTSX
    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
    dataset = builder.build(symbol)

    out_dir = Path("data/export")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "ngh6_dataset.csv"
    builder.export_csv(dataset, str(out_path))

    print(dataset.head())
    print(f"OK: saved {out_path} rows={len(dataset)}")


if __name__ == "__main__":
    main()
