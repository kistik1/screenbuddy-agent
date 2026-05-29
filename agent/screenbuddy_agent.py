from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from agent.conversation_state import (
    ConversationSessionStore,
    WatchSearchIntent,
)
from agent.feedback_handler import (
    apply_feedback,
    feedback_refinement_question,
    is_negative_feedback,
)
from agent.policy import next_follow_up, should_recommend
from agent.recommendation_ranker import (
    format_personal_recommendations,
    rank_recommendations,
)
from agent.search_intent_builder import build_watch_search_intent
from agent.state_extractor import extract_state, is_greeting_only_message


SearchFn = Callable[..., List[Dict[str, Any]]]
ExplanationFn = Callable[..., str]


@dataclass
class AgentResponse:
    message: str
    searched: bool = False
    intent: WatchSearchIntent | None = None


class ScreenBuddyAgent:
    def __init__(
        self,
        store: ConversationSessionStore,
        search_fn: SearchFn,
        explanation_fn: ExplanationFn,
        search_context: Dict[str, Any],
        top_n: int = 3,
        min_similarity: float = 0.2,
    ) -> None:
        self.store = store
        self.search_fn = search_fn
        self.explanation_fn = explanation_fn
        self.search_context = search_context
        self.top_n = top_n
        self.min_similarity = min_similarity

    def reset(self, chat_id: int) -> None:
        self.store.clear(chat_id)

    def handle_message(self, chat_id: int, text: str) -> AgentResponse:
        clean_text = text.strip()
        session = self.store.get_or_create(chat_id)
        session.add_message(clean_text)

        if (
            len(session.messages) == 1
            and is_greeting_only_message(clean_text)
        ):
            session.follow_up_count += 1
            self.store.set(session)
            return AgentResponse(
                message="Hey, how are you? Want to watch something?"
            )

        if session.awaiting_feedback:
            changed = apply_feedback(session, clean_text)
            if changed:
                return self._recommend(session)
            if is_negative_feedback(clean_text):
                session.awaiting_feedback = False
                self.store.set(session)
                return AgentResponse(message=feedback_refinement_question())

        extracted = extract_state(clean_text, session.conversation_text())
        session.user_state.merge(extracted)

        if should_recommend(session):
            return self._recommend(session)

        session.follow_up_count += 1
        self.store.set(session)
        return AgentResponse(
            message=next_follow_up(session, clean_text)
        )

    def _recommend(self, session) -> AgentResponse:
        intent = build_watch_search_intent(session.user_state)
        parsed_query = intent.to_search_query()
        recommendations = self.search_fn(
            user_query=session.conversation_text(),
            parsed_query=parsed_query,
            top_n=self.top_n,
            min_similarity=self.min_similarity,
            **self.search_context,
        )
        ranked = rank_recommendations(recommendations, intent)
        explanation = self.explanation_fn(
            user_query=session.conversation_text(),
            parsed_query=parsed_query,
            recommendations=ranked,
        )
        message = format_personal_recommendations(
            recommendations=ranked,
            intent=intent,
            llm_explanation=explanation,
        )
        session.last_intent = intent
        session.last_recommendations = ranked
        session.awaiting_feedback = True
        self.store.set(session)
        return AgentResponse(
            message=message,
            searched=True,
            intent=intent,
        )
