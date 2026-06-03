from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal

from agent.conversation_state import ConversationSession, WatchSearchIntent
from services.llm_service import OPENAI_MODEL, client, load_prompt


DialoguePhase = Literal[
    "greeting",
    "discovery_follow_up",
    "recommendations",
    "no_results",
    "feedback_clarification",
    "off_topic",
    "session_reset",
    "help",
]


@dataclass
class DialogueContext:
    phase: DialoguePhase
    latest_user_message: str = ""
    session: ConversationSession | None = None
    follow_up_target: str | None = None
    intent: WatchSearchIntent | None = None
    recommendations: List[Dict[str, Any]] = field(default_factory=list)


DialogueFn = Callable[[DialogueContext], str]


def generate_dialogue(context: DialogueContext) -> str:
    if not client:
        return _fallback_dialogue(context)

    payload = _build_payload(context)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("generate_dialogue.txt"),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        return _telegram_plain_text(text) or _fallback_dialogue(context)
    except Exception as error:
        print(f"OpenAI dialogue error: {error}")
        return _fallback_dialogue(context)


def _build_payload(context: DialogueContext) -> Dict[str, Any]:
    session = context.session
    return {
        "phase": context.phase,
        "latest_user_message": context.latest_user_message,
        "conversation": session.conversation_text() if session else "",
        "user_state": (
            session.user_state.to_dict()
            if session
            else {}
        ),
        "follow_up_count": session.follow_up_count if session else 0,
        "follow_up_target": context.follow_up_target,
        "awaiting_feedback": session.awaiting_feedback if session else False,
        "search_filters": session.search_filters if session else {},
        "search_intent": (
            context.intent.to_search_query()
            if context.intent
            else None
        ),
        "recommendations": _safe_recommendations(context.recommendations),
        "instructions": {
            "ask_one_question_max": True,
            "avoid_mood_form": True,
            "recommendations_must_ask_if_right": (
                context.phase == "recommendations"
            ),
            "do_not_invent_catalog_facts": True,
            "off_topic_must_redirect_to_watch_choices": (
                context.phase == "off_topic"
            ),
        },
    }


def _safe_recommendations(
    recommendations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    safe_items: List[Dict[str, Any]] = []
    for item in recommendations[:3]:
        safe_items.append(
            {
                "title": item.get("title"),
                "description": item.get("description"),
                "genres": item.get("genres"),
                "release_year": item.get("release_year"),
                "duration": item.get("duration"),
                "target_audience": item.get("target_audience"),
                "age_category": item.get("age_category"),
                "streaming": item.get("streaming"),
                "type": item.get("type"),
                "similarity_score": item.get("similarity_score"),
                "cluster_name": item.get("cluster_name"),
            }
        )
    return safe_items


def _telegram_plain_text(text: str) -> str:
    return html.escape(text.strip())


def _fallback_dialogue(context: DialogueContext) -> str:
    if context.phase == "greeting":
        return "Hey, how are you? Want to watch something?"
    if context.phase == "session_reset":
        return "Fresh start. Tell me what kind of night you are having, and I will help you find something that fits."
    if context.phase == "help":
        return "Tell me what you feel like watching, or how your day has been. I will ask one question at a time and then recommend a few picks."
    if context.phase == "feedback_clarification":
        return "Got it. What felt off about them?"
    if context.phase == "off_topic":
        return "I am ScreenBuddy, so I can help you choose something to watch. Tell me what kind of mood or night you are in, and I will find a movie or show that fits."
    if context.phase == "no_results":
        return "I am not finding a strong match yet. Should I make it lighter, funnier, cozier, or more exciting?"
    if context.phase == "recommendations":
        return _fallback_recommendations(context.recommendations)
    return _fallback_follow_up(context)


def _fallback_follow_up(context: DialogueContext) -> str:
    target = context.follow_up_target
    if target == "mood":
        return "How was your day today?"
    if target == "content_complexity":
        return "Do you want something easygoing, or are you up for something more absorbing?"
    if target == "preferred_length":
        return "Do you want a quick watch, or something you can settle into?"
    if target == "genre_or_constraint":
        return "Is there anything I should steer toward or away from?"
    return "What do you want the watch to do for you tonight?"


def _fallback_recommendations(
    recommendations: List[Dict[str, Any]],
) -> str:
    if not recommendations:
        return _fallback_dialogue(
            DialogueContext(phase="no_results")
        )

    lines = ["I found a few that could fit:"]
    for item in recommendations[:3]:
        title = html.escape(str(item.get("title") or "Unknown title"))
        genres = html.escape(str(item.get("genres") or ""))
        year = html.escape(str(item.get("release_year") or ""))
        duration = html.escape(str(item.get("duration") or ""))
        metadata = " | ".join(
            value for value in (genres, year, duration) if value
        )
        if metadata:
            lines.append(f"<b>{title}</b> - {metadata}")
        else:
            lines.append(f"<b>{title}</b>")
    lines.append("Do these feel right, or should I tune the search?")
    return "\n\n".join(lines)
