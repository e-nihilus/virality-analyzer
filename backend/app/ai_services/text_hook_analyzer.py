"""Text hook analyser — detects verbal hooks from transcript segments.

For uploaded videos, Qwen is the default contextual/multilingual classifier.
Regex is only used when explicitly configured, so English-only patterns are not
silently presented as AI hooks.
"""

from __future__ import annotations

import logging
import os
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
NONE = "none"
_HOOK_TYPES = {CURIOSITY_GAP, URGENCY, CONFLICT, QUESTION, COMMAND, SURPRISE}

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


def _detect_hooks_regex(segments: list[TranscriptSegment]) -> list[TextHook]:
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


class _QwenHookClassifier:
    _MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None

    def _load_model(self) -> None:
        if self._model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("Loading Qwen hook classifier model %s …", self._MODEL_ID)
        self._tokenizer = AutoTokenizer.from_pretrained(self._MODEL_ID, trust_remote_code=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = AutoModelForCausalLM.from_pretrained(
            self._MODEL_ID,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
        )
        self._model = self._model.to(device)
        self._model.eval()

    def classify(self, text: str) -> tuple[str, float]:
        import torch

        self._load_model()
        prompt = (
            "Classify this transcript segment as exactly one of: "
            "curiosity_gap, urgency, conflict, question, command, surprise, none. "
            "Then rate confidence from 0 to 1. Works in any language.\n"
            f"Segment: {text!r}\n"
            "Output only: label, confidence"
        )
        messages = [
            {"role": "system", "content": "You classify short-form video verbal hooks."},
            {"role": "user", "content": prompt},
        ]
        text_input = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(text_input, return_tensors="pt")
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        with torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=32,
                temperature=0.1,
                do_sample=False,
            )
        generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
        raw = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip().lower()
        return _parse_qwen_hook_output(raw)


_QWEN_CLASSIFIER: _QwenHookClassifier | None = None


def _parse_qwen_hook_output(raw: str) -> tuple[str, float]:
    label = NONE
    for candidate in [*_HOOK_TYPES, NONE]:
        if candidate in raw:
            label = candidate
            break

    confidence = 0.0
    match = re.search(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", raw)
    if match:
        confidence = float(match.group(0))
    elif label != NONE:
        confidence = 0.65
    return label, min(1.0, max(0.0, confidence))


def classify_hooks_llm(segments: list[TranscriptSegment]) -> list[TextHook]:
    """Classify transcript hooks with Qwen, falling back at caller level on errors."""
    global _QWEN_CLASSIFIER

    if _QWEN_CLASSIFIER is None:
        _QWEN_CLASSIFIER = _QwenHookClassifier()

    hooks: list[TextHook] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        label, confidence = _QWEN_CLASSIFIER.classify(text)
        if label in _HOOK_TYPES and confidence >= 0.45:
            hooks.append(TextHook(
                text=text,
                hook_type=label,
                timestamp=segment.start,
                confidence=confidence,
            ))
    hooks.sort(key=lambda h: h.timestamp)
    logger.debug("Qwen detected %d text hooks across %d segments", len(hooks), len(segments))
    return hooks


def detect_hooks(segments: list[TranscriptSegment]) -> list[TextHook]:
    """Detect verbal hooks using regex or Qwen according to TEXT_HOOK_ANALYZER."""
    provider = (
        os.environ.get("TEXT_HOOK_ANALYZER")
        or os.environ.get("AUREA_TEXT_HOOK_ANALYZER")
        or "qwen"
    ).strip().lower()

    if provider == "qwen":
        return classify_hooks_llm(segments)
    if provider == "regex":
        return _detect_hooks_regex(segments)

    raise ValueError(f"Unknown TEXT_HOOK_ANALYZER={provider}")


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
