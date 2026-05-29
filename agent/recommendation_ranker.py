from __future__ import annotations

import html
from typing import Any, Dict, List

from agent.conversation_state import WatchSearchIntent


def rank_recommendations(
    recommendations: List[Dict[str, Any]],
    intent: WatchSearchIntent,
) -> List[Dict[str, Any]]:
    return sorted(
        recommendations,
        key=lambda item: _fit_score(item, intent),
        reverse=True,
    )


def format_personal_recommendations(
    recommendations: List[Dict[str, Any]],
    intent: WatchSearchIntent,
    llm_explanation: str = "",
) -> str:
    if not recommendations:
        return (
            "I couldn't find a strong match yet. Want to steer me toward "
            "something lighter, funnier, cozier, or more exciting?"
        )

    lines = ["I found a few that feel like they could fit:"]
    if llm_explanation:
        lines.append(html.escape(llm_explanation))

    for item in recommendations[:3]:
        title = html.escape(str(item.get("title", "Unknown title")))
        reason = html.escape(_reason_for_item(item, intent))
        vibe = html.escape(_vibe_for_item(item, intent))
        metadata = _metadata(item)
        lines.append(f"<b>{title}</b> — {reason}")
        lines.append(f"Vibe: {vibe}{metadata}")

    lines.append("Do these feel right, or should I tune the search?")
    return "\n\n".join(lines)


def _fit_score(item: Dict[str, Any], intent: WatchSearchIntent) -> float:
    score = float(item.get("similarity_score") or 0)
    searchable = " ".join(
        str(item.get(key, "")).lower()
        for key in ("genres", "description", "cluster_name")
    )

    if intent.intensity_tolerance == "low":
        if any(word in searchable for word in ("light", "family", "comedy")):
            score += 0.08
        if any(word in searchable for word in ("horror", "violent")):
            score -= 0.2
    if intent.desired_feeling and "funny" in intent.desired_feeling:
        if "comedy" in searchable:
            score += 0.1
    if intent.desired_feeling and "comfort" in intent.desired_feeling:
        if any(word in searchable for word in ("family", "heart", "warm")):
            score += 0.08
    return score


def _reason_for_item(
    item: Dict[str, Any],
    intent: WatchSearchIntent,
) -> str:
    desired = intent.desired_feeling or "the vibe you described"
    if intent.energy_level == "low":
        return (
            f"it matches {desired} without asking too much from a tired brain."
        )
    if intent.intensity_tolerance == "low":
        return f"it leans into {desired} and should stay pretty easygoing."
    if intent.current_mood == "bored":
        return f"it should give you the {desired} you asked for without dragging."
    return f"it lines up with {desired} based on the mood and details you shared."


def _vibe_for_item(
    item: Dict[str, Any],
    intent: WatchSearchIntent,
) -> str:
    genres = str(item.get("genres") or "unknown")
    if intent.intensity_tolerance == "low":
        return f"gentle, accessible, {genres.lower()}"
    if intent.desired_feeling:
        return f"{intent.desired_feeling}, {genres.lower()}"
    return genres


def _metadata(item: Dict[str, Any]) -> str:
    values = []
    for key in ("type", "release_year", "duration", "streaming"):
        value = str(item.get(key) or "").strip()
        if value and value.lower() != "unknown":
            values.append(html.escape(value))
    if not values:
        return ""
    return f" ({' | '.join(values)})"

