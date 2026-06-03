from __future__ import annotations

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
