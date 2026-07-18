from __future__ import annotations

import os
import socket
import subprocess
from dataclasses import dataclass
from urllib.request import urlopen

import psycopg2


SOURCE_VERSION = "MARKETCORE_UI_ACCESS_HEALTH_V1"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///finam_core")
INTERNAL_BASE_URL = os.getenv("MARKETCORE_INTERNAL_BASE_URL", "http://127.0.0.1:8080")
EXTERNAL_BASE_URL = os.getenv("MARKETCORE_EXTERNAL_BASE_URL", "http://onezh.ddns.net:18080")
EXPECTED_SERVER_IP = os.getenv("MARKETCORE_EXPECTED_SERVER_IP", "10.0.1.3")


@dataclass(frozen=True)
class Probe:
    home: bool
    research: bool
    i18n: bool

    @property
    def healthy(self) -> bool:
        return self.home and self.research and self.i18n


def contains(url: str, marker: str, timeout: float = 8.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
        return response.status == 200 and marker in body
    except Exception:
        return False


def probe(base_url: str) -> Probe:
    base = base_url.rstrip("/")
    return Probe(
        home=contains(f"{base}/", "MarketCore OS"),
        research=contains(f"{base}/api/v2/domain-render-tree/research", "operator.research.v2"),
        i18n=contains(f"{base}/api/v2/i18n/catalog?locale=ru-RU", "marketcore.i18n_catalog.v2"),
    )


def server_ip() -> str:
    try:
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=3, check=False)
        addresses = result.stdout.split()
        return EXPECTED_SERVER_IP if EXPECTED_SERVER_IP in addresses else (addresses[0] if addresses else "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def service_status() -> str:
    result = subprocess.run(
        ["systemctl", "is-active", "marketcore-ui-shell.service"],
        capture_output=True, text=True, timeout=5, check=False,
    )
    return result.stdout.strip().upper() or "UNKNOWN"


def main() -> int:
    internal = probe(INTERNAL_BASE_URL)
    external = probe(EXTERNAL_BASE_URL)
    current_ip = server_ip()
    service = service_status()
    ip_ok = current_ip == EXPECTED_SERVER_IP
    internal_status = "READY" if internal.healthy and service == "ACTIVE" and ip_ok else "FAILED"
    external_status = "READY" if external.healthy else "FAILED"
    recovery_required = internal_status == "FAILED"
    if recovery_required:
        overall_status, reason_code = "FAILED", "INTERNAL_UI_UNAVAILABLE"
    elif external_status == "FAILED":
        overall_status, reason_code = "DEGRADED", "EXTERNAL_ROUTE_UNAVAILABLE"
    else:
        overall_status, reason_code = "READY", "ACCESS_HEALTHY"

    with psycopg2.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketcore_ui.marketcore_ui_access_health_v1 (
                    internal_status,external_status,overall_status,server_ip,expected_server_ip,
                    external_port,ui_service_status,internal_home_ok,internal_research_ok,internal_i18n_ok,
                    external_home_ok,external_research_ok,external_i18n_ok,reason_code,recovery_required,source_version
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (internal_status,external_status,overall_status,current_ip,EXPECTED_SERVER_IP,18080,service,
                 internal.home,internal.research,internal.i18n,external.home,external.research,external.i18n,
                 reason_code,recovery_required,SOURCE_VERSION),
            )
            cursor.execute(
                "DELETE FROM marketcore_ui.marketcore_ui_access_health_v1 WHERE checked_at < now() - interval '30 days'"
            )
    print(f"status={overall_status} internal={internal_status} external={external_status} ip={current_ip} reason={reason_code}")
    return 2 if recovery_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
