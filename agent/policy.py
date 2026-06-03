from __future__ import annotations

from typing import Literal

from agent.conversation_state import ConversationSession


MAX_AGENT_FOLLOW_UPS = 3
FollowUpTarget = Literal[
    "mood",
    "viewing_intent",
    "content_complexity",
    "preferred_length",
    "genre_or_constraint",
]


def should_recommend(session: ConversationSession) -> bool:
    state = session.user_state
    if state.has_emotional_signal() and state.has_directional_signal():
        return True
    if state.confidence >= 0.75 and state.has_emotional_signal():
        return True
    if session.follow_up_count >= MAX_AGENT_FOLLOW_UPS:
        return bool(session.messages)
    return False


def next_follow_up_target(
    session: ConversationSession,
) -> FollowUpTarget:
    state = session.user_state

    if not state.has_emotional_signal() or state.desired_feeling == "unknown":
        return "viewing_intent"

    if state.intensity_tolerance == "unknown":
        return "content_complexity"

    if not state.genres and state.runtime_preference == "unknown":
        return "preferred_length"

    return "genre_or_constraint"
