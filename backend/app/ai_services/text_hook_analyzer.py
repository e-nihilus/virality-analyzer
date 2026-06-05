"""Text hook analyser — detects verbal hooks (curiosity gap, urgency,
conflict, etc.) from transcript segments using rule-based pattern matching."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..schemas.analysis import Insight, InsightSeverity

if TYPE_CHECKING:
    from .speech_analyzer import TranscriptSegment

logger = logging.getLogger(__name__)

# ─── Hook type constants ────────────────────────────────────────────

CURIOSITY_GAP = "curiosity_gap"
URGENCY = "urgency"
CONFLICT = "conflict"
QUESTION = "question"
COMMAND = "command"
SURPRISE = "surprise"

# ─── Pattern definitions ────────────────────────────────────────────

_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    CURIOSITY_GAP: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"you won'?t believe",
            r"here'?s the secret",
            r"nobody talks about",
            r"what happens next",
            r"the truth about",
            r"what they don'?t tell you",
        ]
    ],
    URGENCY: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"right now",
            r"before it'?s too late",
            r"don'?t miss",
            r"limited time",
            r"hurry",
            r"last chance",
        ]
    ],
    CONFLICT: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bvs\b",
            r"\bbut\b",
            r"\bhowever\b",
            r"the problem is",
            r"\bwrong\b",
            r"\bmistake\b",
            r"\bcontroversial\b",
        ]
    ],
    QUESTION: [
        re.compile(r"\?\s*$"),
    ],
    COMMAND: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"^\s*watch\b",
            r"^\s*listen\b",
            r"^\s*look\b",
            r"^\s*stop\b",
            r"^\s*wait\b",
            r"^\s*check this\b",
        ]
    ],
    SURPRISE: [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bshocking\b",
            r"\binsane\b",
            r"\bunbelievable\b",
            r"\bmind-blowing\b",
            r"\bincredible\b",
            r"\bcrazy\b",
        ]
    ],
}


@dataclass
class TextHook:
    text: str
    hook_type: str
    timestamp: float
    confidence: float


# ─── Detection ──────────────────────────────────────────────────────


def _confidence_for_match_count(count: int) -> float:
    if count >= 3:
        return 0.95
    if count == 2:
        return 0.8
    return 0.6


def detect_hooks(segments: list[TranscriptSegment]) -> list[TextHook]:
    """Scan transcript segments for verbal hook patterns.

    Returns a list of :class:`TextHook` instances sorted by timestamp.
    """
    hooks: list[TextHook] = []

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        matched_types: list[str] = []

        for hook_type, patterns in _PATTERNS.items():
            for pattern in patterns:
                if pattern.search(text):
                    matched_types.append(hook_type)
                    break  # one match per category per segment

        if not matched_types:
            continue

        confidence = _confidence_for_match_count(len(matched_types))

        for hook_type in matched_types:
            hooks.append(TextHook(
                text=text,
                hook_type=hook_type,
                timestamp=segment.start,
                confidence=confidence,
            ))

    hooks.sort(key=lambda h: h.timestamp)
    logger.debug("Detected %d text hooks across %d segments", len(hooks), len(segments))
    return hooks


# ─── Insight generation ─────────────────────────────────────────────


def generate_hook_insights(hooks: list[TextHook], duration: float) -> list[Insight]:
    """Produce up to 3 :class:`Insight` objects from detected text hooks."""
    insights: list[Insight] = []

    early_hooks = [h for h in hooks if h.timestamp <= 3.0]
    missing_early = not any(h.timestamp <= 5.0 for h in hooks)

    # ── 1. Strong verbal hook in the first 3 seconds ────────────────
    if early_hooks:
        best = max(early_hooks, key=lambda h: h.confidence)
        insights.append(Insight(
            title="Strong Verbal Hook",
            description=(
                f"A {best.hook_type.replace('_', ' ')} hook (\"{best.text}\") "
                f"appears at T+{best.timestamp:.1f}s with {best.confidence:.0%} "
                "confidence. Early verbal hooks significantly boost stop rates."
            ),
            severity=InsightSeverity.high,
            timestamp=best.timestamp,
            action="Keep this verbal hook — it complements the visual opening.",
        ))

    # ── 2. No verbal hook in the first 5 seconds ────────────────────
    if missing_early:
        insights.append(Insight(
            title="Missing Verbal Hook",
            description=(
                "No verbal hook patterns detected in the first 5 seconds. "
                "Adding a curiosity gap or direct question can increase "
                "early engagement."
            ),
            severity=InsightSeverity.medium,
            timestamp=0.0,
            action=(
                "Open with a question, teaser, or urgency phrase (e.g. "
                "\"You won't believe…\" or \"Watch this before…\") to "
                "capture attention alongside the visual hook."
            ),
        ))

    # ── 3. Curiosity gap hooks as engagement boosters ────────────────
    curiosity_hooks = [h for h in hooks if h.hook_type == CURIOSITY_GAP]
    if curiosity_hooks and len(insights) < 3:
        first = curiosity_hooks[0]
        insights.append(Insight(
            title="Curiosity Gap Detected",
            description=(
                f"A curiosity gap phrase (\"{first.text}\") at T+{first.timestamp:.1f}s "
                "creates an open loop that encourages viewers to keep watching. "
                f"{len(curiosity_hooks)} curiosity hook(s) found in total."
            ),
            severity=InsightSeverity.low,
            timestamp=first.timestamp,
            action=(
                "Curiosity gaps are strong engagement drivers. Delay the "
                "payoff slightly to maximise watch time."
            ),
        ))

    return insights[:3]
