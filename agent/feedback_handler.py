from __future__ import annotations

import re

from agent.conversation_state import ConversationSession


NEGATIVE_FEEDBACK = (
    "no",
    "not it",
    "not quite",
    "try again",
    "wrong vibe",
    "don't like",
    "do not like",
)


def is_negative_feedback(message: str) -> bool:
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in NEGATIVE_FEEDBACK)


def apply_feedback(
    session: ConversationSession,
    message: str,
) -> bool:
    lowered = message.lower()
    changed = False

    filter_updates = extract_filter_refinements(message)
    if filter_updates:
        session.search_filters.update(filter_updates)
        changed = True

    if "more fun" in lowered or "funnier" in lowered or "playful" in lowered:
        session.user_state.desired_feeling = "funny and uplifting"
        session.user_state.intensity_tolerance = "low"
        changed = True
    if "lighter" in lowered or "too heavy" in lowered:
        session.user_state.intensity_tolerance = "low"
        session.user_state.avoid_genres = _append_once(
            session.user_state.avoid_genres,
            "heavy",
        )
        changed = True
    if "too boring" in lowered or "more exciting" in lowered:
        session.user_state.desired_feeling = "exciting fun"
        session.user_state.energy_level = "medium"
        changed = True
    if "cozier" in lowered or "more cozy" in lowered:
        session.user_state.desired_feeling = "comfort"
        session.user_state.intensity_tolerance = "low"
        changed = True

    session.user_state.free_text_context = session.conversation_text()
    return changed


def extract_filter_refinements(message: str) -> dict[str, object]:
    lowered = message.lower()
    updates: dict[str, object] = {}

    content_type = _extract_content_type(lowered)
    if content_type:
        updates["type"] = content_type

    audience = _extract_target_audience(lowered)
    if audience:
        updates["target_audience"] = audience

    duration = _extract_duration_preference(lowered)
    if duration:
        updates["duration_preference"] = duration

    streaming = _extract_streaming(lowered)
    if streaming:
        updates["streaming"] = streaming

    age_category = _extract_age_category(lowered)
    if age_category:
        updates["age_category"] = age_category

    release_year_min = _extract_year_after(lowered)
    if release_year_min:
        updates["release_year_min"] = release_year_min

    release_year_max = _extract_year_before(lowered)
    if release_year_max:
        updates["release_year_max"] = release_year_max

    return updates


def feedback_refinement_question() -> str:
    return "Got it — was it too heavy, too boring, or just the wrong vibe?"


def _append_once(values: list[str], value: str) -> list[str]:
    if value not in values:
        return values + [value]
    return values


def _extract_content_type(lowered: str) -> str | None:
    if re.search(r"\b(no|not|not any|without)\s+(movies?|films?)\b", lowered):
        return "TV Show"
    if re.search(r"\b(no|not|not any|without)\s+(tv\s*)?shows?\b", lowered):
        return "Movie"
    if re.search(r"\b(tv\s*shows?|series|episodes?|seasons?)\b", lowered):
        return "TV Show"
    if re.search(r"\bshows?\b", lowered) and "show me" not in lowered:
        return "TV Show"
    if re.search(r"\b(movies?|films?)\b", lowered):
        return "Movie"
    return None


def _extract_target_audience(lowered: str) -> str | None:
    if re.search(r"\b(kids?|children|child)\b", lowered):
        return "kids"
    if re.search(r"\b(family|families)\b", lowered):
        return "family"
    if re.search(r"\b(teens?|teenagers?|young adult)\b", lowered):
        return "teens"
    if re.search(r"\b(adults?|grown[- ]?ups?)\b", lowered):
        return "adults"
    return None


def _extract_duration_preference(lowered: str) -> str | None:
    if re.search(r"\b(shorter|short|quick|brief|not too long)\b", lowered):
        return "short"
    if re.search(r"\b(medium|moderate|normal length)\b", lowered):
        return "medium"
    if re.search(r"\b(longer|long|binge|epic)\b", lowered):
        return "long"
    return None


def _extract_streaming(lowered: str) -> str | None:
    platforms = (
        ("amazon prime", ("amazon prime", "prime video", "prime")),
        ("netflix", ("netflix",)),
        ("hulu", ("hulu",)),
        ("disney", ("disney", "disney+")),
        ("hbo", ("hbo", "max")),
        ("apple", ("apple tv", "apple tv+")),
    )
    for canonical, phrases in platforms:
        if any(phrase in lowered for phrase in phrases):
            return canonical
    return None


def _extract_age_category(lowered: str) -> str | None:
    if re.search(r"\b(classic|classics|older|old)\b", lowered):
        return "classic"
    if re.search(r"\b(recent|newest|latest|newer)\b", lowered):
        return "recent"
    if re.search(r"\b(modern)\b", lowered):
        return "modern"
    return None


def _extract_year_after(lowered: str) -> int | None:
    match = re.search(r"\b(?:after|since|from)\s+(19\d{2}|20\d{2})\b", lowered)
    if match:
        return int(match.group(1))
    return None


def _extract_year_before(lowered: str) -> int | None:
    match = re.search(r"\b(?:before|until|pre[- ]?)\s*(19\d{2}|20\d{2})\b", lowered)
    if match:
        return int(match.group(1))
    return None
