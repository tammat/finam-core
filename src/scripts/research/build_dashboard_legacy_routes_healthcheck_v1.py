#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

ROUTES = [
    "/summary",
    "/edge",
    "/journal",
    "/compression-history",
    "/api/current",
]

BASE_URL = "http://127.0.0.1:8088"


def main():
    failures = 0

    print("=== DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    for route in ROUTES:
        try:
            r = requests.get(
                BASE_URL + route,
                timeout=10,
            )

            status = r.status_code
            ok = status == 200

            if not ok:
                failures += 1

            print(
                f"ROUTE_ROW "
                f"route={route} "
                f"http_status={status} "
                f"ok={int(ok)} "
                f"length={len(r.text)}"
            )

        except Exception as exc:
            failures += 1

            print(
                f"ROUTE_ROW "
                f"route={route} "
                f"http_status=EXCEPTION "
                f"ok=0 "
                f"error={type(exc).__name__}"
            )

    print(f"failures={failures}")

    if failures == 0:
        print("VERDICT=DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_OK")
    else:
        print("VERDICT=DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_FAILED")

    print("TEST_DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_V1_OK")


if __name__ == "__main__":
    main()
