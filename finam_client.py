# finam_client.py
# SHIM: единый источник истины находится в finam_core.clients.finam_client

from finam_core.clients.finam_client import FinamClient  # noqa: F401

__all__ = ["FinamClient"]