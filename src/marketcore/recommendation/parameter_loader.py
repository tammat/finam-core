from __future__ import annotations

from decimal import Decimal

import psycopg2
import psycopg2.extras


class PlatformParameterLoader:

    def load(self) -> dict[str, object]:

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                cur.execute("""
                    SELECT
                        parameter_code,
                        parameter_type,
                        parameter_value
                    FROM knowledge.platform_parameter_v1
                    WHERE enabled
                    ORDER BY parameter_code
                """)

                result = {}

                for row in cur.fetchall():

                    t = row["parameter_type"]
                    v = row["parameter_value"]

                    if t == "INTEGER":
                        result[row["parameter_code"]] = int(v)

                    elif t == "NUMERIC":
                        result[row["parameter_code"]] = Decimal(v)

                    elif t == "BOOLEAN":
                        result[row["parameter_code"]] = (
                            str(v).lower() in (
                                "1",
                                "true",
                                "yes",
                                "on"
                            )
                        )

                    else:
                        result[row["parameter_code"]] = str(v)

                return result
