from __future__ import annotations

import json
from typing import Any, Dict, Literal

from services.llm_service import (
    OPENAI_MODEL,
    client,
    load_prompt,
    safe_json_loads,
)


FollowUpIntent = Literal[
    "accept",
    "reject",
    "refine",
    "ask_question",
    "ambiguous",
]

QUESTION_TYPES = {
    "constraint_acceptability",
    "search_capability",
    "other",
    "none",
}
REFINEMENT_FIELDS = {
    "streaming",
    "type",
    "duration_preference",
    "target_audience",
    "age_category",
    "release_year_min",
    "release_year_max",
}
VIBE_FIELDS = {
    "desired_feeling",
    "intensity_tolerance",
    "energy_level",
    "avoid_genres",
}

DEFAULT_FOLLOW_UP_RESULT: Dict[str, Any] = {
    "intent": "ambiguous",
    "user_question": "",
    "question_type": "none",
    "refinements": {},
    "vibe_adjustment": {},
    "needs_clarification": True,
    "reason": "",
}


def analyze_post_recommendation_follow_up(
    message: str,
    conversation_text: str = "",
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    clean_message = message.strip()
    if not clean_message or not client:
        return DEFAULT_FOLLOW_UP_RESULT.copy()

    payload = {
        "conversation": conversation_text,
        "latest_user_message": clean_message,
        "context": context or {},
    }

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": load_prompt(
                        "analyze_feedback_follow_up.txt"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        parsed = safe_json_loads(content, DEFAULT_FOLLOW_UP_RESULT)
        return _normalize_follow_up_result(parsed)
    except Exception as error:
        print(f"OpenAI feedback follow-up analysis error: {error}")
        return DEFAULT_FOLLOW_UP_RESULT.copy()


def _normalize_follow_up_result(parsed: Dict[str, Any]) -> Dict[str, Any]:
    result = DEFAULT_FOLLOW_UP_RESULT.copy()

    intent = _normalize_intent(parsed.get("intent"))
    result["intent"] = intent
    result["user_question"] = str(parsed.get("user_question") or "").strip()
    result["question_type"] = _normalize_question_type(
        parsed.get("question_type")
    )
    result["refinements"] = _normalize_mapping(
        parsed.get("refinements"),
        REFINEMENT_FIELDS,
    )
    result["vibe_adjustment"] = _normalize_mapping(
        parsed.get("vibe_adjustment"),
        VIBE_FIELDS,
    )
    result["needs_clarification"] = bool(
        parsed.get("needs_clarification", intent == "ambiguous")
    )
    result["reason"] = str(parsed.get("reason") or "").strip()
    return result


def _normalize_intent(value: Any) -> FollowUpIntent:
    normalized = str(value or "ambiguous").strip().lower()
    if normalized in {
        "accept",
        "reject",
        "refine",
        "ask_question",
        "ambiguous",
    }:
        return normalized  # type: ignore[return-value]
    return "ambiguous"


def _normalize_question_type(value: Any) -> str:
    normalized = str(value or "none").strip().lower()
    if normalized in QUESTION_TYPES:
        return normalized
    return "none"


def _normalize_mapping(
    value: Any,
    allowed_fields: set[str],
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    normalized: Dict[str, Any] = {}
    for key, raw_item in value.items():
        if key not in allowed_fields or raw_item in (None, "", [], {}):
            continue
        normalized[key] = raw_item
    return normalized


__all__ = [
    "FollowUpIntent",
    "analyze_post_recommendation_follow_up",
]
