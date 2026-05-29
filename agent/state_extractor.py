from __future__ import annotations

from typing import Iterable, List

from agent.conversation_state import UserPreferenceState
from services.user_state_analyzer import (
    analyze_user_state,
    is_greeting_only_message,
)


GENRE_KEYWORDS = {
    "action",
    "adventure",
    "animation",
    "comedy",
    "crime",
    "documentary",
    "drama",
    "fantasy",
    "horror",
    "romance",
    "sci-fi",
    "thriller",
}


def extract_state(message: str, conversation_text: str) -> UserPreferenceState:
    analysis = analyze_user_state(conversation_text)
    legacy_state = analysis.get("user_state", {})
    genres = _extract_genres(message)
    avoid_genres = list(legacy_state.get("avoid", []))

    lowered = message.lower()
    for genre in GENRE_KEYWORDS:
        if f"no {genre}" in lowered or f"not {genre}" in lowered:
            avoid_genres.append(genre)

    return UserPreferenceState(
        current_mood=_map_mood(legacy_state.get("mood")),
        desired_feeling=_map_intent(legacy_state.get("viewing_intent")),
        energy_level=legacy_state.get("energy_level", "unknown"),
        intensity_tolerance=_map_intensity(
            legacy_state.get("content_complexity"),
            avoid_genres,
        ),
        genres=genres,
        avoid_genres=_unique(avoid_genres),
        runtime_preference=legacy_state.get("preferred_length", "unknown"),
        free_text_context=conversation_text,
        confidence=legacy_state.get("confidence", 0.0),
    )


def _map_mood(value: str | None) -> str:
    return value or "unknown"


def _map_intent(value: str | None) -> str:
    mapping = {
        "relax": "easy comfort",
        "escape": "distraction and escape",
        "laugh": "funny and uplifting",
        "get_excited": "exciting fun",
        "feel_comforted": "comfort",
        "think_deeply": "thoughtful",
    }
    return mapping.get(value or "unknown", "unknown")


def _map_intensity(
    content_complexity: str | None,
    avoid_genres: Iterable[str],
) -> str:
    if content_complexity == "low":
        return "low"
    if content_complexity == "high":
        return "high"
    if any(item in {"heavy", "violent", "horror"} for item in avoid_genres):
        return "low"
    return "unknown"


def _extract_genres(message: str) -> List[str]:
    lowered = message.lower()
    return [
        genre
        for genre in sorted(GENRE_KEYWORDS)
        if genre in lowered
        and f"no {genre}" not in lowered
        and f"not {genre}" not in lowered
    ]


def _unique(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    for value in values:
        normalized = str(value).strip().lower()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


__all__ = [
    "extract_state",
    "is_greeting_only_message",
]

