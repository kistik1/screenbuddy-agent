from __future__ import annotations

from typing import Any, Dict, Literal

from services.llm_service import (
    OPENAI_MODEL,
    client,
    load_prompt,
    safe_json_loads,
)


TopicClassification = Literal["in_scope", "off_topic", "unclear"]

DEFAULT_TOPIC_RESULT: Dict[str, Any] = {
    "classification": "unclear",
    "reason": "",
}

WATCH_TERMS = {
    "movie",
    "movies",
    "film",
    "films",
    "show",
    "shows",
    "series",
    "tv",
    "watch",
    "netflix",
    "stream",
    "streaming",
    "recommend",
    "recommendation",
}

GREETING_TERMS = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "good morning",
    "good afternoon",
    "good evening",
}

MOOD_TERMS = {
    "sad",
    "tired",
    "stressed",
    "bored",
    "happy",
    "exhausted",
    "drained",
    "anxious",
    "overwhelmed",
    "relax",
    "comfort",
    "funny",
    "light",
    "heavy",
}

OFF_TOPIC_TERMS = {
    "trip",
    "travel",
    "hotel",
    "flight",
    "itinerary",
    "recipe",
    "weather",
    "code",
    "coding",
    "python",
    "javascript",
    "homework",
    "news",
}

FEEDBACK_TERMS = {
    "ok",
    "okay",
    "yes",
    "thanks",
    "thank you",
    "no",
    "not it",
    "too",
    "more",
    "less",
    "shorter",
    "longer",
    "only",
    "netflix",
    "movie",
    "movies",
    "show",
    "shows",
}


def classify_message_topic(
    message: str,
    awaiting_feedback: bool = False,
) -> TopicClassification:
    clean_message = message.strip()
    if not clean_message:
        return "unclear"

    obvious_classification = _obvious_in_scope(
        clean_message,
        awaiting_feedback,
    )
    if obvious_classification:
        return obvious_classification

    if not client:
        return _heuristic_classification(clean_message, awaiting_feedback)

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("classify_topic.txt"),
                },
                {
                    "role": "user",
                    "content": (
                        f"awaiting_feedback={awaiting_feedback}\n"
                        f"message={clean_message}"
                    ),
                },
            ],
        )
        content = response.choices[0].message.content.strip()
        parsed = safe_json_loads(content, DEFAULT_TOPIC_RESULT)
        return _normalize_classification(parsed.get("classification"))
    except Exception as error:
        print(f"OpenAI topic router error: {error}")
        return _heuristic_classification(clean_message, awaiting_feedback)


def _normalize_classification(value: Any) -> TopicClassification:
    normalized = str(value or "unclear").strip().lower()
    if normalized in {"in_scope", "off_topic", "unclear"}:
        return normalized  # type: ignore[return-value]
    return "unclear"


def _heuristic_classification(
    message: str,
    awaiting_feedback: bool,
) -> TopicClassification:
    lowered = message.lower()

    if any(term in lowered for term in WATCH_TERMS):
        return "in_scope"

    if awaiting_feedback and any(term in lowered for term in FEEDBACK_TERMS):
        return "in_scope"

    if any(term in lowered for term in MOOD_TERMS):
        return "in_scope"

    if any(term in lowered for term in OFF_TOPIC_TERMS):
        return "off_topic"

    return "unclear"


def _obvious_in_scope(
    message: str,
    awaiting_feedback: bool,
) -> TopicClassification | None:
    lowered = message.lower().strip()
    cleaned = "".join(
        char for char in lowered if char.isalnum() or char.isspace()
    ).strip()

    if cleaned in GREETING_TERMS:
        return "in_scope"

    if any(term in lowered for term in WATCH_TERMS):
        return "in_scope"

    if awaiting_feedback and any(term in lowered for term in FEEDBACK_TERMS):
        return "in_scope"

    if any(term in lowered for term in MOOD_TERMS):
        return "in_scope"

    return None


__all__ = ["TopicClassification", "classify_message_topic"]
