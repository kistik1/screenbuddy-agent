from __future__ import annotations

from agent.conversation_state import ConversationSession
from agent.state_extractor import is_greeting_only_message


MAX_AGENT_FOLLOW_UPS = 2


def should_recommend(session: ConversationSession) -> bool:
    state = session.user_state
    if state.has_emotional_signal() and state.has_directional_signal():
        return True
    if state.confidence >= 0.75 and state.has_emotional_signal():
        return True
    if session.follow_up_count >= MAX_AGENT_FOLLOW_UPS:
        return bool(session.messages)
    return False


def next_follow_up(session: ConversationSession, latest_message: str) -> str:
    state = session.user_state
    lowered = latest_message.lower().strip()

    if len(session.messages) == 1 and is_greeting_only_message(latest_message):
        return "Hey, how are you? Want to watch something?"

    if any(
        phrase in lowered
        for phrase in (
            "help me find",
            "find something",
            "what should i watch",
            "recommend",
        )
    ) and not state.has_directional_signal():
        return "I'd be happy to find something for you. How was your day today?"

    if not state.has_emotional_signal():
        return (
            "Do you want something that lifts you up, distracts you, "
            "or just keeps you company?"
        )

    if state.intensity_tolerance == "unknown":
        return (
            "Are you in the mood for easy comfort or something that grabs "
            "your brain a bit?"
        )

    if not state.genres and state.runtime_preference == "unknown":
        return "Got it. More cozy-funny, or more exciting-fun?"

    return "What should I steer toward or away from?"
