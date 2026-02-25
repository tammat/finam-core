import sys
from pathlib import Path
from storage.postgres import PostgresStorage
sys.path.append(str(Path(__file__).resolve().parents[1]))
storage = PostgresStorage()

print("OFFLINE MODE:", storage.offline)
print("DSN:", storage.dsn)
