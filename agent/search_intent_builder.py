from __future__ import annotations

from typing import Any

from agent.conversation_state import UserPreferenceState, WatchSearchIntent


def build_watch_search_intent(
    state: UserPreferenceState,
    search_filters: dict[str, Any] | None = None,
) -> WatchSearchIntent:
    filters = search_filters or {}
    return WatchSearchIntent(
        desired_feeling=_known_or_none(state.desired_feeling),
        current_mood=_known_or_none(state.current_mood),
        energy_level=_known_or_none(state.energy_level),
        intensity_tolerance=_known_or_none(state.intensity_tolerance),
        genres=state.genres,
        avoid_genres=state.avoid_genres,
        runtime_preference=(
            filters.get("duration_preference")
            or _runtime_or_none(state.runtime_preference)
        ),
        language_preference=_known_or_none(state.language_preference),
        platform_preference=(
            filters.get("streaming")
            or _known_or_none(state.platform_preference)
        ),
        release_year_min=filters.get("release_year_min"),
        release_year_max=filters.get("release_year_max"),
        target_audience=filters.get("target_audience"),
        age_category=filters.get("age_category"),
        content_type=filters.get("type"),
        free_text_context=state.free_text_context,
    )


def _known_or_none(value: str) -> str | None:
    return value if value and value != "unknown" else None


def _runtime_or_none(value: str) -> str | None:
    return value if value in {"short", "medium", "long"} else None
