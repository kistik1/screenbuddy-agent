from __future__ import annotations

from typing import Any, Dict, Literal

from services.llm_service import (
    OPENAI_MODEL,
    client,
    load_prompt,
    safe_json_loads,
)


FeedbackIntent = Literal["accepted", "refine", "negative", "ambiguous"]

DEFAULT_FEEDBACK_INTENT_RESULT: Dict[str, Any] = {
    "intent": "ambiguous",
    "reason": "",
}

ACCEPTANCE_PHRASES = {
    "ok",
    "okay",
    "yes",
    "yeah",
    "yep",
    "sounds good",
    "great",
    "thanks",
    "thank you",
    "cool",
    "fine",
    "works",
    "good",
    "i'll watch",
    "ill watch",
}

REFINEMENT_CUES = {
    "more",
    "less",
    "only",
    "too",
    "different",
    "shorter",
    "longer",
    "netflix",
    "movie",
    "movies",
    "show",
    "shows",
    "tv",
    "again",
}

NEGATIVE_CUES = {
    "no",
    "not",
    "not it",
    "not quite",
    "bad recommendation",
    "bad recommend",
    "don't like",
    "do not like",
    "wrong recommendation",
    "wrong vibe",
}


def classify_feedback_intent(
    message: str,
    conversation_text: str = "",
) -> FeedbackIntent:
    clean_message = message.strip()
    if not clean_message:
        return "ambiguous"

    if not client:
        return _heuristic_feedback_intent(clean_message)

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("classify_feedback_intent.txt"),
                },
                {
                    "role": "user",
                    "content": (
                        f"conversation={conversation_text}\n"
                        f"latest_user_message={clean_message}"
                    ),
                },
            ],
        )
        content = response.choices[0].message.content.strip()
        parsed = safe_json_loads(content, DEFAULT_FEEDBACK_INTENT_RESULT)
        return _normalize_feedback_intent(parsed.get("intent"))
    except Exception as error:
        print(f"OpenAI feedback intent error: {error}")
        return _heuristic_feedback_intent(clean_message)


def _normalize_feedback_intent(value: Any) -> FeedbackIntent:
    normalized = str(value or "ambiguous").strip().lower()
    if normalized in {"accepted", "refine", "negative", "ambiguous"}:
        return normalized  # type: ignore[return-value]
    return "ambiguous"


def _heuristic_feedback_intent(message: str) -> FeedbackIntent:
    lowered = message.lower().strip()

    if any(cue in lowered for cue in REFINEMENT_CUES):
        return "refine"

    if any(cue in lowered for cue in NEGATIVE_CUES):
        return "negative"

    if lowered in ACCEPTANCE_PHRASES:
        return "accepted"

    if any(phrase in lowered for phrase in ACCEPTANCE_PHRASES):
        return "accepted"

    return "ambiguous"


__all__ = ["FeedbackIntent", "classify_feedback_intent"]
