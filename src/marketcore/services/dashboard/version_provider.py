from __future__ import annotations

import subprocess

from marketcore.presentation.viewmodels.executive_overview_vm import HomeVersionVM


def _safe_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:
        return "UNKNOWN"


class VersionProvider:
    def load(self) -> HomeVersionVM:
        return HomeVersionVM(
            product_name="MarketCore",
            product_subtitle="Trading Intelligence Platform",
            product_version="1.0.0",
            dashboard_version="1.0.0",
            repo="finam-core",
            git_commit=_safe_git(["rev-parse", "--short", "HEAD"]),
            git_tag=_safe_git(["describe", "--tags", "--abbrev=0"]),
        )
