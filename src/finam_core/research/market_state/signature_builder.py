import hashlib

from .result import ClassifierResult


class SignatureBuilder:
    # Строит человекочитаемую и компактную сигнатуры состояния рынка.

    def build_canonical(self, results: tuple[ClassifierResult, ...]) -> str:
        parts = [f"{item.group}={item.state}" for item in sorted(results, key=lambda x: x.group)]
        return "|".join(parts)

    def build_compact(self, canonical_signature: str) -> str:
        digest = hashlib.sha256(canonical_signature.encode("utf-8")).hexdigest()
        return f"MS-{digest[:12].upper()}"
