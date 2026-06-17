from __future__ import annotations

import pytest

from app.ai_services import text_hook_analyzer
from app.ai_services.speech_analyzer import TranscriptSegment


def test_qwen_hook_classifier_does_not_fall_back_to_regex(monkeypatch):
    monkeypatch.setenv("TEXT_HOOK_ANALYZER", "qwen")
    monkeypatch.setattr(
        text_hook_analyzer,
        "classify_hooks_llm",
        lambda _segments: (_ for _ in ()).throw(RuntimeError("qwen failed")),
    )

    with pytest.raises(RuntimeError):
        text_hook_analyzer.detect_hooks([
            TranscriptSegment(start=0.0, end=1.0, text="You won't believe this"),
        ])


def test_regex_hooks_only_when_explicitly_configured(monkeypatch):
    monkeypatch.setenv("TEXT_HOOK_ANALYZER", "regex")

    hooks = text_hook_analyzer.detect_hooks([
        TranscriptSegment(start=0.0, end=1.0, text="You won't believe this"),
    ])

    assert hooks
    assert hooks[0].hook_type == text_hook_analyzer.CURIOSITY_GAP
