from __future__ import annotations

import json
from dataclasses import dataclass

import psycopg2


I18N_CATALOG_V2_MEDIA_TYPE = "application/vnd.marketcore.i18n-catalog+json; charset=utf-8"


@dataclass(frozen=True, slots=True)
class I18nCatalogHttpResponseV2:
    status_code: int
    content_type: str
    body: bytes


def _storage_locale(locale_code: str) -> str:
    normalized = locale_code.strip().replace("_", "-").lower()
    if normalized in {"ru", "ru-ru"}:
        return "ru"
    raise ValueError(f"I18N_CATALOG_V2_LOCALE_UNSUPPORTED:{locale_code}")


def i18n_catalog_http_v2(locale_code: str = "ru-RU") -> I18nCatalogHttpResponseV2:
    storage_locale = _storage_locale(locale_code)
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT resource_key, caption
                FROM presentation.ui_resource_v1
                WHERE locale_code = %s
                ORDER BY resource_key
                """,
                (storage_locale,),
            )
            messages = {str(key): str(caption) for key, caption in cursor.fetchall()}

    payload = {
        "schema_version": "marketcore.i18n_catalog.v2",
        "locale_code": "ru-RU",
        "fallback_locale_code": "ru-RU",
        "messages": messages,
    }
    return I18nCatalogHttpResponseV2(
        status_code=200,
        content_type=I18N_CATALOG_V2_MEDIA_TYPE,
        body=json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )
