from __future__ import annotations


class NumberFormatter:
    @staticmethod
    def compact(value: int | float | None) -> str:
        if value is None:
            return "0"
        n = float(value)
        abs_n = abs(n)
        if abs_n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.1f}B".rstrip("0").rstrip(".")
        if abs_n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M".rstrip("0").rstrip(".")
        if abs_n >= 1_000:
            return f"{n / 1_000:.0f}K"
        return str(int(n))
