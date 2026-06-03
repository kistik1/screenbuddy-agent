from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from agent.conversation_state import (
    ConversationSessionStore,
    WatchSearchIntent,
)
from agent.dialogue_generator import (
    DialogueContext,
    DialogueFn,
    generate_dialogue,
)
from agent.feedback_handler import (
    apply_feedback,
    extract_filter_refinements,
    is_negative_feedback,
)
from agent.policy import next_follow_up_target, should_recommend
from agent.recommendation_ranker import rank_recommendations
from agent.search_intent_builder import build_watch_search_intent
from agent.state_extractor import extract_state, is_greeting_only_message
from agent.topic_router import classify_message_topic
from services.session_intent_analyzer import classify_feedback_intent


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
        search_context: Dict[str, Any],
        explanation_fn: ExplanationFn | None = None,
        dialogue_fn: DialogueFn = generate_dialogue,
        top_n: int = 3,
        min_similarity: float = 0.2,
    ) -> None:
        self.store = store
        self.search_fn = search_fn
        self.explanation_fn = explanation_fn
        self.dialogue_fn = dialogue_fn
        self.search_context = search_context
        self.top_n = top_n
        self.min_similarity = min_similarity

    def reset(self, chat_id: int) -> None:
        self.store.clear(chat_id)

    def handle_message(self, chat_id: int, text: str) -> AgentResponse:
        clean_text = text.strip()
        session = self.store.get_or_create(chat_id)

        topic_classification = classify_message_topic(
            clean_text,
            awaiting_feedback=session.awaiting_feedback,
        )
        if topic_classification == "off_topic":
            return AgentResponse(
                message=self.dialogue_fn(
                    DialogueContext(
                        phase="off_topic",
                        latest_user_message=clean_text,
                        session=session,
                    )
                )
            )

        session.add_message(clean_text)

        if (
            len(session.messages) == 1
            and is_greeting_only_message(clean_text)
        ):
            session.follow_up_count += 1
            self.store.set(session)
            return AgentResponse(
                message=self.dialogue_fn(
                    DialogueContext(
                        phase="greeting",
                        latest_user_message=clean_text,
                        session=session,
                    )
                )
            )

        if session.awaiting_feedback:
            feedback_intent = classify_feedback_intent(
                clean_text,
                session.conversation_text(),
            )
            if feedback_intent == "accepted":
                self.store.clear(chat_id)
                return AgentResponse(message="Good watching time.")

            changed = apply_feedback(session, clean_text)
            if changed:
                return self._recommend(session)
            if (
                feedback_intent == "negative"
                or is_negative_feedback(clean_text)
            ):
                session.awaiting_feedback = False
                self.store.set(session)
                return AgentResponse(
                    message=self.dialogue_fn(
                        DialogueContext(
                            phase="feedback_clarification",
                            latest_user_message=clean_text,
                            session=session,
                        )
                    )
                )

        extracted = extract_state(clean_text, session.conversation_text())
        session.user_state.merge(extracted)
        filter_updates = extract_filter_refinements(clean_text)
        if filter_updates:
            session.search_filters.update(filter_updates)

        if should_recommend(session):
            return self._recommend(session)

        session.follow_up_count += 1
        self.store.set(session)
        return AgentResponse(
            message=self.dialogue_fn(
                DialogueContext(
                    phase="discovery_follow_up",
                    latest_user_message=clean_text,
                    session=session,
                    follow_up_target=next_follow_up_target(session),
                )
            )
        )

    def _recommend(self, session) -> AgentResponse:
        intent = build_watch_search_intent(
            session.user_state,
            session.search_filters,
        )
        parsed_query = intent.to_search_query()
        recommendations = self.search_fn(
            user_query=session.conversation_text(),
            parsed_query=parsed_query,
            top_n=self.top_n,
            min_similarity=self.min_similarity,
            **self.search_context,
        )
        ranked = rank_recommendations(recommendations, intent)
        phase = "recommendations" if ranked else "no_results"
        message = self.dialogue_fn(
            DialogueContext(
                phase=phase,
                latest_user_message=(
                    session.messages[-1] if session.messages else ""
                ),
                session=session,
                intent=intent,
                recommendations=ranked,
            )
        )
        session.last_intent = intent
        session.last_recommendations = ranked
        session.awaiting_feedback = bool(ranked)
        self.store.set(session)
        return AgentResponse(
            message=message,
            searched=True,
            intent=intent,
        )
