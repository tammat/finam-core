# finam_client.py
# SHIM: совместимость legacy-импортов `from finam_client import FinamClient`.
# Делает автодетект сигнатуры SoT finam_core.clients.finam_client.FinamClient.

from __future__ import annotations

import os
import inspect
from finam_core.clients.finam_client import FinamClient as _SoTFinamClient

__all__ = ["FinamClient"]


class FinamClient(_SoTFinamClient):
    def __init__(self, *args, **kwargs):
        """
        Поддерживаем оба варианта SoT:
          A) FinamClient(host, account_id, jwt='', secret='')
          B) FinamClient(host, personal_token)

        При вызове FinamClient() без аргументов — берём из env.
        """
        sig = inspect.signature(_SoTFinamClient.__init__)
        params = sig.parameters

        # Если пользователь явно передал аргументы — пробуем как есть
        if args or kwargs:
            super().__init__(*args, **kwargs)
            return

        host = os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST") or "api.finam.ru:443"

        if "personal_token" in params:
            token = (
                os.getenv("FINAM_PERSONAL_TOKEN")
                or os.getenv("FINAM_SECRET")
                or os.getenv("FINAM_TOKEN")
                or ""
            )
            if not token:
                raise RuntimeError("FINAM_PERSONAL_TOKEN (or FINAM_SECRET/FINAM_TOKEN) is required")
            super().__init__(host=host, personal_token=token)
            return

        # иначе A) host + account_id + jwt/secret
        account_id = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or ""
        jwt = os.getenv("FINAM_JWT") or ""
        secret = os.getenv("FINAM_SECRET") or os.getenv("FINAM_TOKEN") or ""

        # account_id может быть не нужен для marketdata/bars, но SoT требует — дадим пустую строку
        # (если SoT валидирует — тогда положи FINAM_ACCOUNT_ID в env)
        super().__init__(host=host, account_id=account_id, jwt=jwt, secret=secret)