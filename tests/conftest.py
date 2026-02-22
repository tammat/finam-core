import sys
from pathlib import Path
import importlib.util
import importlib.util

def _has_finam_proto() -> bool:
    return importlib.util.find_spec("finam_proto") is not None

collect_ignore = []
if not _has_finam_proto():
    collect_ignore += [
        "test_accounts.py",
        "test_auth.py",
        "test_auth_clean.py",
        "test_auth_min.py",
        "test_real_connection.py",
    ]

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _has_finam_proto() -> bool:
    return importlib.util.find_spec("finam_proto") is not None


import sys
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _has_finam_proto() -> bool:
    return importlib.util.find_spec("finam_proto") is not None

_GRPC_TESTS = {
    "test_auth.py",
    "test_auth_clean.py",
    "test_auth_min.py",
    "test_accounts.py",
    "test_real_connection.py",
}

def pytest_ignore_collect(*args, **kwargs):
    """
    Compatible with pytest<8 and pytest>=8:
      pytest<8: (path, config)
      pytest>=8: (collection_path, config)
    Some plugin paths may call it with kwargs only; handle that too.
    """
    if _has_finam_proto():
        return False

    p = None
    if args:
        p = args[0]
    else:
        p = kwargs.get("collection_path") or kwargs.get("path")

    if p is None:
        return False

    p = Path(str(p))
    return p.name in _GRPC_TESTS