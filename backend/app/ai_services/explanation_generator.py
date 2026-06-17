"""Explanation generator adapters for heuristic and Qwen providers."""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod

from ..schemas.analysis import Insight, InsightSeverity, TimelineEntry, TopClip
from .explanation_engine import generate_insights

from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)


class ExplanationGenerator(ABC):
    """Abstraction for generating natural-language analysis insights."""

    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    @abstractmethod
    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        """Generate insights for the analysis result."""


class HeuristicExplanationGenerator(ExplanationGenerator):
    """Current rule-based explanation generator."""

    provider_name = "heuristic"

    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        return generate_insights(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )


class CachedExplanationGenerator(ExplanationGenerator):
    """Simple in-memory cache wrapper for explanation generation."""

    _GLOBAL_CACHE: dict[str, list[Insight]] = {}

    def __init__(self, inner: ExplanationGenerator) -> None:
        self.inner = inner
        self.provider_name = inner.provider_name
        self._cache = self._GLOBAL_CACHE

    def _cache_key(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> str:
        payload = (
            self.provider_name,
            round(duration, 3),
            round(overall_virality, 3),
            round(retention_score, 3),
            dominant_emotion,
            tuple((e.time_seconds, e.virality, e.valence, e.arousal, e.retention, e.label) for e in timeline),
            tuple((c.start_seconds, c.end_seconds, c.score, c.predicted_retention, tuple(c.reasons or [])) for c in top_clips),
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        key = self._cache_key(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )
        if key not in self._cache:
            self._cache[key] = self.inner.generate(
                timeline=timeline,
                top_clips=top_clips,
                duration=duration,
                overall_virality=overall_virality,
                retention_score=retention_score,
                dominant_emotion=dominant_emotion,
            )
        return list(self._cache[key])


class QwenExplanationGenerator(ExplanationGenerator):
    """Qwen2.5-Instruct explanation provider.

    This provider is restricted to explanation generation only. Viral scores are
    still calculated by heuristic modules in the analysis pipeline.
    """

    _MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
    _SEVERITY_BY_POSITION = [InsightSeverity.high, InsightSeverity.medium, InsightSeverity.low]

    provider_name = "qwen"

    def __init__(self, fallback: ExplanationGenerator | None = None) -> None:
        self._fallback = fallback or HeuristicExplanationGenerator()
        self._model = None
        self._tokenizer = None

    def validate_dependencies(self) -> None:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "Qwen provider requested but required 'torch/transformers' dependencies are not installed"
            ) from exc

    def _load_model(self) -> None:
        """Lazy-load model and tokenizer on first use."""
        if self._model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("Loading Qwen model %s …", self._MODEL_ID)
        self._tokenizer = AutoTokenizer.from_pretrained(self._MODEL_ID, trust_remote_code=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = AutoModelForCausalLM.from_pretrained(
            self._MODEL_ID,
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            trust_remote_code=True,
        )
        self._model = self._model.to(device)
        self._model.eval()
        logger.info("Qwen model loaded successfully.")

    def _build_prompt(
        self,
        *,
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> str:
        clips_summary = "\n".join(
            f"  - Clip {i + 1}: {c.start_seconds:.1f}s–{c.end_seconds:.1f}s (score {c.score:.2f})"
            for i, c in enumerate(top_clips[:5])
        )
        return (
            "You are a short-form video virality expert. Analyze the following metrics "
            "and provide exactly 3 actionable insights about this video's viral potential.\n\n"
            f"Overall virality score: {overall_virality:.2f}\n"
            f"Retention score: {retention_score:.2f}\n"
            f"Video duration: {duration:.1f}s\n"
            f"Dominant emotion: {dominant_emotion}\n"
            f"Top clips:\n{clips_summary}\n\n"
            "Output exactly 3 insights, one per line, in this format:\n"
            "TITLE: <short title> | DESCRIPTION: <explanation> | ACTION: <recommended action>\n\n"
            "Do not include numbering, bullet points, or any other text outside this format."
        )

    def _parse_insights(self, text: str) -> list[Insight] | None:
        """Parse model output into Insight objects. Returns None on failure."""
        insights: list[Insight] = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or "TITLE:" not in line:
                continue
            try:
                parts = line.split("|")
                fields: dict[str, str] = {}
                for part in parts:
                    part = part.strip()
                    for key in ("TITLE:", "DESCRIPTION:", "ACTION:"):
                        if part.upper().startswith(key):
                            fields[key] = part[len(key):].strip()
                            break
                if "TITLE:" not in fields or "DESCRIPTION:" not in fields:
                    continue
                severity = self._SEVERITY_BY_POSITION[min(len(insights), 2)]
                insights.append(
                    Insight(
                        title=fields["TITLE:"],
                        description=fields["DESCRIPTION:"],
                        severity=severity,
                        action=fields.get("ACTION:"),
                    )
                )
                if len(insights) >= 3:
                    break
            except Exception:
                continue
        return insights if insights else None

    def generate_clip_reasons(self, candidate_context: dict) -> list[str]:
        """Generate 1-2 clip reasons using only supplied evidence."""
        self.validate_dependencies()
        try:
            import torch

            self._load_model()
            prompt = (
                "Describe why this exact video segment is a strong clip using only the provided evidence. "
                "Return 1-2 concise reasons. Do not invent objects, faces, emotions, audio, or speech. "
                "If evidence is weak, say which measured signal selected it.\n\n"
                f"Evidence JSON:\n{json.dumps(candidate_context, ensure_ascii=False, sort_keys=True)}\n\n"
                "Return only the reasons, one per line."
            )
            messages = [
                {"role": "system", "content": "You write evidence-grounded short-form video clip reasons."},
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
                    max_new_tokens=128,
                    temperature=0.2,
                    do_sample=False,
                )

            generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
            raw_output = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
            reasons = _parse_clip_reason_lines(raw_output)
            if reasons:
                return reasons
            raise ValueError("Qwen clip reason output was empty or unparsable")
        except Exception:
            logger.warning("Qwen clip reason generation failed", exc_info=True)
            raise

    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        self.validate_dependencies()

        fallback_kwargs = dict(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )

        try:
            import torch

            self._load_model()

            prompt = self._build_prompt(
                top_clips=top_clips,
                duration=duration,
                overall_virality=overall_virality,
                retention_score=retention_score,
                dominant_emotion=dominant_emotion,
            )

            messages = [
                {"role": "system", "content": "You are a video virality analysis assistant."},
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
                    max_new_tokens=512,
                    temperature=0.7,
                    do_sample=True,
                )

            generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
            raw_output = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
            logger.debug("Qwen raw output: %s", raw_output)

            insights = self._parse_insights(raw_output)
            if insights:
                return insights

            logger.warning("Failed to parse Qwen output, falling back to heuristic.")
        except Exception:
            logger.warning("Qwen inference failed, falling back to heuristic.", exc_info=True)

        return self._fallback.generate(**fallback_kwargs)


def _parse_clip_reason_lines(text: str) -> list[str]:
    reasons: list[str] = []
    for line in text.strip().splitlines():
        cleaned = line.strip().lstrip("-•0123456789. )\t").strip()
        if not cleaned:
            continue
        reasons.append(cleaned[:180])
        if len(reasons) >= 2:
            break
    return reasons


def generate_clip_reasons_qwen(candidate_context: dict) -> list[str]:
    """Convenience entry point for Qwen-backed clip reasons."""
    return QwenExplanationGenerator().generate_clip_reasons(candidate_context)
