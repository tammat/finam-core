from __future__ import annotations

import psycopg2

from marketcore.presentation.i18n.registry import ALLOWED_PREFIXES, UI_RESOURCES

SOURCE_VERSION = "MARKETCORE_UI_I18N_ARCHITECTURE_V1"


def main() -> None:
    invalid = [
        r.resource_key
        for r in UI_RESOURCES
        if not r.resource_key.startswith(ALLOWED_PREFIXES)
    ]
    if invalid:
        raise SystemExit(f"INVALID_I18N_PREFIXES={invalid}")

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor() as cur:
            for r in UI_RESOURCES:
                cur.execute(
                    """
                    INSERT INTO presentation.ui_resource_v1
                    (
                        resource_key,
                        locale_code,
                        caption,
                        caption_short,
                        caption_mobile,
                        tooltip,
                        icon,
                        resource_group
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(resource_key, locale_code) DO UPDATE SET
                        caption=EXCLUDED.caption,
                        caption_short=EXCLUDED.caption_short,
                        caption_mobile=EXCLUDED.caption_mobile,
                        tooltip=EXCLUDED.tooltip,
                        icon=EXCLUDED.icon,
                        resource_group=EXCLUDED.resource_group,
                        updated_at=now();
                    """,
                    (
                        r.resource_key,
                        r.locale_code,
                        r.caption,
                        r.caption_short,
                        r.caption_mobile,
                        r.tooltip,
                        r.icon,
                        r.resource_group,
                    ),
                )

    print("=== MARKETCORE_UI_I18N_ARCHITECTURE_V1 ===")
    print(f"resources_registered={len(UI_RESOURCES)}")
    print("invalid_prefixes=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_UI_I18N_ARCHITECTURE_V1_READY")


if __name__ == "__main__":
    main()
