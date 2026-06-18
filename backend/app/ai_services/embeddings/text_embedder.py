"""Text window embedding adapters."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re

from ...processing.window_builder import TimeWindow


@dataclass(frozen=True)
class TextSegmentInput:
    start: float
    end: float
    text: str


class HashingTextEmbedder:
    """Deterministic text embedder for transcript segments.

    This gives the training pipeline a stable text vector today without adding
    a heavyweight sentence-transformer dependency. Model-backed text embedders
    can later replace it behind the same window contract.
    """

    provider_name = "hashing_text_fallback"
    dimension = 32

    def __init__(self, dimension: int | None = None) -> None:
        if dimension is not None:
            self.dimension = max(1, int(dimension))

    def embed_windows(
        self,
        *,
        windows: list[TimeWindow],
        segments: list[TextSegmentInput],
    ) -> list[list[float]]:
        return [self._embed_text(_text_for_window(window, segments)) for window in windows]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = _tokenize(text)
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]


def _text_for_window(window: TimeWindow, segments: list[TextSegmentInput]) -> str:
    overlapping: list[str] = []
    for segment in segments:
        if segment.end <= window.start_seconds or segment.start >= window.end_seconds:
            continue
        if segment.text:
            overlapping.append(segment.text)
    return " ".join(overlapping)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", text.lower())
