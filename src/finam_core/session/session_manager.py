# Patched SessionManager (FORTS-aware)

from datetime import datetime


class SessionManager:
    def get_regime(self, symbol: str | None = None):
        now = datetime.now()
        h = now.hour
        m = now.minute
        wd = now.weekday()

        # === WEEKEND BLOCK ===
        if wd >= 5:
            return {"phase": "weekend", "allow_entries": False}

        # === FORTS DETECT ===
        if symbol and "@" in symbol:
            return self._forts_session(h, m)

        # fallback (stocks)
        return self._stock_session(h, m)

    # =========================================================
    # === FORTS SESSION ===
    # =========================================================
    def _forts_session(self, h, m):
        # 09:00–18:45
        if (h > 9 and h < 18) or (h == 9) or (h == 18 and m < 45):
            return {"phase": "core", "allow_entries": True}

        # break 18:45–19:00
        if h == 18 and m >= 45:
            return {"phase": "break", "allow_entries": False}

        # evening 19:00–23:50
        if (h >= 19 and h < 23) or (h == 23 and m <= 50):
            return {"phase": "evening", "allow_entries": True}

        return {"phase": "closed", "allow_entries": False}

    # =========================================================
    # === STOCK SESSION (fallback)
    # =========================================================
    def _stock_session(self, h, m):
        # 07:00–09:50
        if (h == 7) or (h == 8) or (h == 9 and m < 50):
            return {"phase": "morning", "allow_entries": True}

        # 10:00–18:40
        if (h >= 10 and h < 18) or (h == 18 and m < 40):
            return {"phase": "core", "allow_entries": True}

        # 19:00–23:50
        if (h >= 19 and h < 23) or (h == 23 and m <= 50):
            return {"phase": "evening", "allow_entries": True}

        return {"phase": "closed", "allow_entries": False}
