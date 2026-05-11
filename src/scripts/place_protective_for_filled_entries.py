# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)


def main() -> int:
    print("PROTECTIVE_PLACEMENT_CHECK")
    print("mode=dry_run")
    print("auto_real_protective_enabled=", os.getenv("AUTO_REAL_PROTECTIVE_ORDERS", "0"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
