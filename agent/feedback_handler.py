from __future__ import annotations

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


def feedback_refinement_question() -> str:
    return "Got it — was it too heavy, too boring, or just the wrong vibe?"


def _append_once(values: list[str], value: str) -> list[str]:
    if value not in values:
        return values + [value]
    return values

