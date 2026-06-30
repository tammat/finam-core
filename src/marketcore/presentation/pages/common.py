from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def html_escape(v) -> str:
    return str(v if v is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetchall(sql: str, params=None):
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def fetchone(sql: str, params=None):
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def simple_table(rows, cols):
    head = "".join(f"<th>{html_escape(c)}</th>" for c in cols)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(f"<td>{html_escape(r[c])}</td>" for c in cols) + "</tr>"
    return f'<table border="1" cellpadding="8" cellspacing="0"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
