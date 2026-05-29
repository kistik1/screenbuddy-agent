from __future__ import annotations

from agent.conversation_state import UserPreferenceState, WatchSearchIntent


def build_watch_search_intent(
    state: UserPreferenceState,
) -> WatchSearchIntent:
    return WatchSearchIntent(
        desired_feeling=_known_or_none(state.desired_feeling),
        current_mood=_known_or_none(state.current_mood),
        energy_level=_known_or_none(state.energy_level),
        intensity_tolerance=_known_or_none(state.intensity_tolerance),
        genres=state.genres,
        avoid_genres=state.avoid_genres,
        runtime_preference=_runtime_or_none(state.runtime_preference),
        language_preference=_known_or_none(state.language_preference),
        platform_preference=_known_or_none(state.platform_preference),
        free_text_context=state.free_text_context,
    )


def _known_or_none(value: str) -> str | None:
    return value if value and value != "unknown" else None


def _runtime_or_none(value: str) -> str | None:
    return value if value in {"short", "medium", "long"} else None

