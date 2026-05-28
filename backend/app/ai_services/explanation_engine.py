"""Explanation engine — converts structured timeline features into
human-readable, actionable insights without requiring an LLM."""

from __future__ import annotations

from ..schemas.analysis import (
    Insight,
    InsightSeverity,
    TimelineEntry,
    TopClip,
)


def generate_insights(
    timeline: list[TimelineEntry],
    top_clips: list[TopClip],
    duration: float,
    overall_virality: float,
    retention_score: float,
    dominant_emotion: str,
) -> list[Insight]:
    """Produce a prioritised list of insights from analysis signals."""
    insights: list[Insight] = []

    if not timeline:
        return insights

    virality = [e.virality or 0.0 for e in timeline]
    retention = [e.retention or 0.0 for e in timeline]
    arousal = [e.arousal or 0.0 for e in timeline]
    valence = [e.valence or 0.0 for e in timeline]

    # ── 1. Hook analysis (first 3 seconds) ──────────────────────────
    insights.extend(_hook_insights(virality, timeline))

    # ── 2. Pattern disruption peaks ─────────────────────────────────
    insights.extend(_disruption_insights(virality, timeline))

    # ── 3. Retention dips ───────────────────────────────────────────
    insights.extend(_retention_dip_insights(retention, timeline, duration))

    # ── 4. Emotional arc ────────────────────────────────────────────
    insights.extend(_emotion_arc_insights(arousal, valence, timeline, dominant_emotion))

    # ── 5. Pacing analysis ──────────────────────────────────────────
    insights.extend(_pacing_insights(virality, duration))

    # ── 6. Clip-level reasoning ─────────────────────────────────────
    insights.extend(_clip_insights(top_clips))

    # ── 7. Overall score explanation ────────────────────────────────
    insights.extend(
        _overall_score_insights(overall_virality, retention_score, duration)
    )

    # ── 8. Ending strength ──────────────────────────────────────────
    insights.extend(_ending_insights(virality, retention, timeline))

    return insights


# ─── Rule implementations ───────────────────────────────────────────


def _hook_insights(
    virality: list[float], timeline: list[TimelineEntry],
) -> list[Insight]:
    if len(virality) < 3:
        return []

    hook_avg = sum(virality[:3]) / 3
    hook_peak = max(virality[:3])

    if hook_avg > 0.65:
        return [Insight(
            title="Strong Opening Hook",
            description=(
                f"The first 3 seconds score {hook_avg:.0%} virality potential. "
                "High visual motion and brightness shifts immediately capture "
                "attention in the scroll-stop window."
            ),
            severity=InsightSeverity.high,
            timestamp=0.0,
            action="Keep this opening structure — it performs well for autoplay feeds.",
        )]

    if hook_avg < 0.35:
        return [Insight(
            title="Weak Opening — Add a Scroll-Stopper",
            description=(
                f"Opening virality is only {hook_avg:.0%}. Most viewers decide "
                "to stay or swipe within the first 1-2 seconds."
            ),
            severity=InsightSeverity.high,
            timestamp=0.0,
            action=(
                "Try a pattern disruption in the first frame: an abrupt zoom, "
                "bold text overlay, unexpected motion, or a direct-to-camera question."
            ),
        )]

    return [Insight(
        title="Moderate Opening Hook",
        description=(
            f"Opening virality is {hook_avg:.0%} — acceptable but not standout. "
            f"Peak within the first 3s reaches {hook_peak:.0%}."
        ),
        severity=InsightSeverity.medium,
        timestamp=0.0,
        action=(
            "Consider starting with a bold visual or text hook to push the "
            "opening above 65% and increase stop rates."
        ),
    )]


def _disruption_insights(
    virality: list[float], timeline: list[TimelineEntry],
) -> list[Insight]:
    if len(virality) < 5:
        return []

    # Find the highest peak outside the first 3 seconds
    peaks: list[tuple[int, float]] = []
    for i in range(3, len(virality) - 1):
        if virality[i] >= virality[i - 1] and virality[i] >= virality[i + 1] and virality[i] > 0.6:
            peaks.append((i, virality[i]))

    peaks.sort(key=lambda x: x[1], reverse=True)
    insights: list[Insight] = []

    for idx, score in peaks[:2]:
        t = timeline[idx].time_seconds
        insights.append(Insight(
            title="Pattern Disruption Detected",
            description=(
                f"A virality spike of {score:.0%} at T+{t:.0f}s indicates a scene "
                "change or motion burst that re-captures attention. This type of "
                "disruption correlates with higher completion rates."
            ),
            severity=InsightSeverity.high,
            timestamp=t,
            action=f"Place your key message or CTA near T+{t:.0f}s to leverage peak attention.",
        ))

    return insights


def _retention_dip_insights(
    retention: list[float],
    timeline: list[TimelineEntry],
    duration: float,
) -> list[Insight]:
    if len(retention) < 6:
        return []

    # Find deepest dip (skip first 2s of startup noise)
    search = retention[2:]
    min_ret = min(search)
    min_idx = retention.index(min_ret, 2)
    min_time = timeline[min_idx].time_seconds

    insights: list[Insight] = []

    if min_ret < 0.5:
        insights.append(Insight(
            title="Critical Retention Drop",
            description=(
                f"Retention drops to {min_ret:.0%} at T+{min_time:.0f}s — a likely "
                "drop-off point. Viewers are losing interest here."
            ),
            severity=InsightSeverity.high,
            timestamp=min_time,
            action=(
                "Add a visual pattern break (cut, zoom, text popup) 1-2 seconds "
                "before this point to prevent the drop-off."
            ),
        ))
    elif min_ret < 0.7:
        insights.append(Insight(
            title="Retention Dip",
            description=(
                f"Retention dips to {min_ret:.0%} at T+{min_time:.0f}s. This segment "
                "has less visual variation than the surrounding content."
            ),
            severity=InsightSeverity.medium,
            timestamp=min_time,
            action=(
                "Consider adding a subtitle, B-roll cut, or motion graphic around "
                f"T+{min_time:.0f}s to maintain momentum."
            ),
        ))

    return insights


def _emotion_arc_insights(
    arousal: list[float],
    valence: list[float],
    timeline: list[TimelineEntry],
    dominant_emotion: str,
) -> list[Insight]:
    if len(arousal) < 5:
        return []

    avg_arousal = sum(arousal) / len(arousal)
    avg_valence = sum(valence) / len(valence)

    # Check for emotional flatness
    arousal_range = max(arousal) - min(arousal)
    insights: list[Insight] = []

    if arousal_range < 0.15:
        insights.append(Insight(
            title="Flat Emotional Arc",
            description=(
                f"Arousal stays within a narrow {arousal_range:.0%} band. "
                "Viral content typically shows emotional peaks and valleys."
            ),
            severity=InsightSeverity.medium,
            action=(
                "Introduce at least one emotional spike — a reveal, surprise, "
                "or tension moment — to create contrast."
            ),
        ))
    elif arousal_range > 0.4:
        peak_idx = arousal.index(max(arousal))
        peak_time = timeline[peak_idx].time_seconds
        insights.append(Insight(
            title="Strong Emotional Dynamics",
            description=(
                f"The video shows wide emotional range ({arousal_range:.0%} arousal spread). "
                f"Dominant emotion: {dominant_emotion}. Peak arousal at T+{peak_time:.0f}s."
            ),
            severity=InsightSeverity.low,
            timestamp=peak_time,
            action="This emotional arc works well — high contrast drives shares and saves.",
        ))

    return insights


def _pacing_insights(virality: list[float], duration: float) -> list[Insight]:
    high_motion_frames = sum(1 for v in virality if v > 0.55)
    ratio = high_motion_frames / max(len(virality), 1)

    if ratio > 0.6:
        return [Insight(
            title="Fast Pacing — High Energy",
            description=(
                f"{ratio:.0%} of the video has above-average visual activity. "
                "This fast pacing works well for short-form and younger audiences."
            ),
            severity=InsightSeverity.low,
            action=(
                "If targeting a broader audience, consider adding 2-3 second "
                "breathing moments between high-energy sections."
            ),
        )]

    if ratio < 0.2 and duration > 15:
        return [Insight(
            title="Slow Pacing — Risk of Drop-off",
            description=(
                f"Only {ratio:.0%} of frames show strong visual activity. For a "
                f"{duration:.0f}s video, this may feel too slow for short-form feeds."
            ),
            severity=InsightSeverity.medium,
            action=(
                "Add more cuts, zooms, or motion graphics throughout. Aim for "
                "a visual change every 2-3 seconds for short-form content."
            ),
        )]

    return []


def _clip_insights(top_clips: list[TopClip]) -> list[Insight]:
    insights: list[Insight] = []

    for i, clip in enumerate(top_clips[:2]):
        clip_dur = clip.end_seconds - clip.start_seconds
        reasons_str = "; ".join(clip.reasons or ["Elevated engagement"])

        insights.append(Insight(
            title=f"Top Clip #{i + 1} — {clip_dur:.0f}s Segment",
            description=(
                f"T+{clip.start_seconds:.0f}s to T+{clip.end_seconds:.0f}s "
                f"(score {clip.score:.0%}, predicted retention {(clip.predicted_retention or 0):.0%}). "
                f"{reasons_str}."
            ),
            severity=InsightSeverity.high if clip.score > 0.7 else InsightSeverity.medium,
            timestamp=clip.start_seconds,
            action=(
                "Export this segment as a standalone clip for Reels/TikTok/Shorts. "
                "Add a hook text overlay in the first frame for maximum impact."
            ),
        ))

    return insights


def _overall_score_insights(
    overall_virality: float, retention_score: float, duration: float,
) -> list[Insight]:
    insights: list[Insight] = []

    if overall_virality > 0.75:
        tier = "high"
        desc = "This video has strong viral potential across most signals."
    elif overall_virality > 0.5:
        tier = "moderate"
        desc = "Viral potential is moderate — specific areas can be improved."
    else:
        tier = "low"
        desc = "Overall virality is below average. Review the suggestions above."

    insights.append(Insight(
        title=f"Overall Potential: {overall_virality:.0%} ({tier.title()})",
        description=(
            f"{desc} Retention: {retention_score:.0%}. "
            f"Duration: {duration:.0f}s."
        ),
        severity=(
            InsightSeverity.high if tier == "low"
            else InsightSeverity.medium if tier == "moderate"
            else InsightSeverity.low
        ),
        action=(
            "Focus on the highest-severity recommendations above to improve scores."
            if tier != "high"
            else "Consider A/B testing with variations of the hook and CTA placement."
        ),
    ))

    return insights


def _ending_insights(
    virality: list[float],
    retention: list[float],
    timeline: list[TimelineEntry],
) -> list[Insight]:
    if len(virality) < 5:
        return []

    last_3 = virality[-3:]
    avg_ending = sum(last_3) / 3
    ret_ending = sum(retention[-3:]) / 3

    if avg_ending < 0.35 and ret_ending < 0.7:
        return [Insight(
            title="Weak Ending — Viewers May Not Complete",
            description=(
                f"The last 3 seconds score only {avg_ending:.0%} virality and "
                f"{ret_ending:.0%} retention. A weak ending reduces shares and saves."
            ),
            severity=InsightSeverity.medium,
            timestamp=timeline[-3].time_seconds,
            action=(
                "End with energy: a punchline, visual payoff, loop-back to the hook, "
                "or a clear CTA. Avoid fading to black or slow-motion endings."
            ),
        )]

    if avg_ending > 0.6:
        return [Insight(
            title="Strong Ending — Loop Potential",
            description=(
                f"Ending virality is {avg_ending:.0%}. If the ending visually connects "
                "to the opening, this creates a rewatch loop that boosts algorithmic ranking."
            ),
            severity=InsightSeverity.low,
            timestamp=timeline[-3].time_seconds,
            action="Consider editing the last frame to match the first for a seamless loop.",
        )]

    return []
