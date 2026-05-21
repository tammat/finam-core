from __future__ import annotations

from finam_core.analytics.statistics_repository import StatisticsRepository


def main() -> int:
    repo = StatisticsRepository()

    sql = """
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'trades'
    ORDER BY ordinal_position
    """

    with repo_connect(repo) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

            print("TRADES_COLUMNS")
            for name, data_type in rows:
                print(f"- {name}: {data_type}")

            cur.execute("SELECT * FROM trades LIMIT 3")
            sample = cur.fetchall()
            colnames = [desc.name for desc in cur.description]

            print("")
            print("TRADES_SAMPLE")
            print(colnames)
            for row in sample:
                print(row)

    return 0


def repo_connect(repo: StatisticsRepository):
    import psycopg
    return psycopg.connect(repo.database_url)


if __name__ == "__main__":
    raise SystemExit(main())
