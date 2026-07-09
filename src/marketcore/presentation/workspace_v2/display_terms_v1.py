from __future__ import annotations

from typing import Any


def load_terms(cur, term_codes: list[str], mode: str = "short") -> dict[str, dict[str, str]]:
    column = {
        "full": "caption_full",
        "short": "caption_short",
        "mobile": "caption_mobile",
    }.get(mode, "caption_short")

    cur.execute(
        f"""
        SELECT
            term_code,
            caption_full,
            caption_short,
            caption_mobile,
            tooltip,
            {column} AS caption
        FROM presentation.workspace_v2_display_term_v1
        WHERE enabled
          AND term_code = ANY(%s)
        """,
        (term_codes,),
    )

    rows = {str(r["term_code"]): dict(r) for r in cur.fetchall()}

    result: dict[str, dict[str, str]] = {}
    for code in term_codes:
        row = rows.get(code)
        if row is None:
            result[code] = {
                "caption": code,
                "tooltip": "",
                "caption_full": code,
                "caption_short": code,
                "caption_mobile": code,
            }
        else:
            result[code] = {
                "caption": str(row.get("caption") or code),
                "tooltip": str(row.get("tooltip") or ""),
                "caption_full": str(row.get("caption_full") or code),
                "caption_short": str(row.get("caption_short") or code),
                "caption_mobile": str(row.get("caption_mobile") or code),
            }
    return result


def term_label(terms: dict[str, dict[str, str]], code: str) -> str:
    return terms.get(code, {}).get("caption", code)


def term_tooltip(terms: dict[str, dict[str, str]], code: str) -> str:
    return terms.get(code, {}).get("tooltip", "")
