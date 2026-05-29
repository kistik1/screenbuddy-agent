import time
from typing import Any, Dict, List

from services.llm_service import (
    OPENAI_MODEL,
    client,
    load_prompt,
    safe_json_loads,
)


MAX_RUNTIME_FOLLOW_UP_QUESTIONS = 1
MAX_ALLOWED_FOLLOW_UP_QUESTIONS = 3
FOLLOW_UP_THRESHOLD = 0.75
KEY_FIELDS = ("mood", "viewing_intent")
GREETING_ONLY_PHRASES = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "good morning",
    "good afternoon",
    "good evening",
}
FOLLOW_UP_PRIORITY = [
    "viewing_intent",
    "mood",
    "content_complexity",
    "preferred_length",
]

ALLOWED_VALUES = {
    "mood": {
        "happy",
        "sad",
        "stressed",
        "tired",
        "bored",
        "neutral",
        "unknown",
    },
    "energy_level": {
        "low",
        "medium",
        "high",
        "unknown",
    },
    "viewing_intent": {
        "relax",
        "escape",
        "laugh",
        "get_excited",
        "feel_comforted",
        "think_deeply",
        "unknown",
    },
    "content_complexity": {
        "low",
        "medium",
        "high",
        "unknown",
    },
    "preferred_length": {
        "short",
        "medium",
        "long",
        "unknown",
    },
}

DEFAULT_USER_STATE = {
    "mood": "unknown",
    "energy_level": "unknown",
    "viewing_intent": "unknown",
    "content_complexity": "unknown",
    "preferred_length": "unknown",
    "avoid": [],
    "confidence": 0.0,
    "missing_info": [],
}

DEFAULT_ANALYZER_RESULT = {
    "user_state": DEFAULT_USER_STATE.copy(),
    "needs_follow_up": True,
    "assistant_reply": "",
    "follow_up_questions": [],
}


def _normalize_enum(field: str, value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    if normalized in ALLOWED_VALUES[field]:
        return normalized
    return "unknown"


def _normalize_avoid(value: Any) -> List[str]:
    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_missing_info(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    valid_fields = list(DEFAULT_USER_STATE.keys())
    valid_fields.remove("confidence")
    valid_fields.remove("missing_info")

    result: List[str] = []
    for item in value:
        field = str(item).strip()
        if field in valid_fields and field not in result:
            result.append(field)
    return result


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0

    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return round(confidence, 2)


def _normalize_assistant_reply(value: Any) -> str:
    return str(value or "").strip()


def _clean_text(text: str) -> str:
    return "".join(
        char.lower() for char in text if char.isalnum() or char.isspace()
    ).strip()


def is_greeting_only_message(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    return cleaned in GREETING_ONLY_PHRASES


def _key_fields_known(user_state: Dict[str, Any]) -> bool:
    return all(user_state.get(field) != "unknown" for field in KEY_FIELDS)


def _calculate_missing_info(user_state: Dict[str, Any]) -> List[str]:
    missing_info = _normalize_missing_info(
        user_state.get("missing_info")
    )

    for field in FOLLOW_UP_PRIORITY:
        value = user_state.get(field)
        if value == "unknown" and field not in missing_info:
            missing_info.append(field)

    return missing_info


def _has_secondary_signal(
    user_state: Dict[str, Any],
) -> bool:
    return any(
        user_state.get(field) != "unknown"
        for field in (
            "content_complexity",
            "preferred_length",
            "energy_level",
        )
    ) or bool(user_state.get("avoid"))


def _should_ask_follow_up(
    user_state: Dict[str, Any],
) -> bool:
    if not _key_fields_known(user_state):
        return True

    if (
        user_state.get("content_complexity") == "unknown"
        and user_state.get("preferred_length") == "unknown"
    ):
        return True

    return (
        user_state["confidence"] < FOLLOW_UP_THRESHOLD
        and not _has_secondary_signal(user_state)
    )


def _select_follow_up_field(
    user_state: Dict[str, Any],
    missing_info: List[str],
) -> str | None:
    for field in FOLLOW_UP_PRIORITY:
        if field not in missing_info:
            continue
        if field == "preferred_length":
            if user_state.get("content_complexity") == "unknown":
                continue
        return field
    return None


def _build_human_follow_up_question(
    user_state: Dict[str, Any],
    field: str | None,
    greeting_only: bool = False,
) -> str:
    mood = user_state.get("mood")
    viewing_intent = user_state.get("viewing_intent")
    complexity = user_state.get("content_complexity")

    if greeting_only:
        return "Hello! What are you in the mood to watch tonight?"

    if field == "mood":
        if viewing_intent == "unknown":
            return "What kind of mood are you in tonight?"
        return "Got it. How are you feeling right now?"

    if field == "viewing_intent":
        if mood == "tired":
            return "Got it. Do you want something comforting, funny, or a bit more exciting?"
        if mood == "sad":
            return "Do you want something comforting, funny, or more distracting?"
        return "What sounds better right now: something comforting, funny, or exciting?"

    if field == "content_complexity":
        if mood in {"tired", "stressed"}:
            return "Got it. Want something light and easy, or are you okay with something a bit deeper?"
        return "Do you want something light and easy, or something a bit deeper?"

    if field == "preferred_length":
        if complexity == "low":
            return "Nice. Do you want a quick watch or something longer?"
        if complexity == "high":
            return "Okay. Are you up for a quick watch or something you can sink into?"
        return "Do you want a quick watch or something longer?"

    return "What sounds good to you right now?"


def _normalize_result(
    raw_result: Dict[str, Any],
    max_follow_up_questions: int,
    greeting_only: bool = False,
) -> Dict[str, Any]:
    result = DEFAULT_ANALYZER_RESULT.copy()
    user_state = DEFAULT_USER_STATE.copy()
    user_state.update(raw_result.get("user_state", {}))

    for field in ALLOWED_VALUES:
        user_state[field] = _normalize_enum(field, user_state.get(field))

    user_state["avoid"] = _normalize_avoid(user_state.get("avoid"))
    user_state["confidence"] = _clamp_confidence(
        user_state.get("confidence")
    )
    user_state["missing_info"] = _calculate_missing_info(user_state)

    needs_follow_up = _should_ask_follow_up(user_state)
    if greeting_only:
        needs_follow_up = True

    follow_up_questions = []
    assistant_reply = _normalize_assistant_reply(
        raw_result.get("assistant_reply")
    )
    if needs_follow_up:
        cap = min(
            max_follow_up_questions,
            MAX_RUNTIME_FOLLOW_UP_QUESTIONS,
            MAX_ALLOWED_FOLLOW_UP_QUESTIONS,
        )
        follow_up_field = _select_follow_up_field(
            user_state,
            user_state["missing_info"],
        )
        if follow_up_field and cap > 0:
            follow_up_questions = [
                _build_human_follow_up_question(
                    user_state,
                    follow_up_field,
                    greeting_only=greeting_only,
                )
            ]
        elif greeting_only and cap > 0:
            follow_up_questions = [
                _build_human_follow_up_question(
                    user_state,
                    None,
                    greeting_only=True,
                )
            ]

    if not assistant_reply and follow_up_questions:
        assistant_reply = follow_up_questions[0]

    result["user_state"] = user_state
    result["needs_follow_up"] = bool(
        needs_follow_up and assistant_reply
    )
    result["assistant_reply"] = assistant_reply
    result["follow_up_questions"] = follow_up_questions
    return result


def _heuristic_state(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    user_state = DEFAULT_USER_STATE.copy()

    if any(word in lowered for word in ["sad", "down", "upset", "heartbroken"]):
        user_state["mood"] = "sad"
        user_state["viewing_intent"] = "feel_comforted"
        user_state["energy_level"] = "low"
    elif any(word in lowered for word in ["exhaust", "tired", "drained", "long day"]):
        user_state["mood"] = "tired"
        user_state["viewing_intent"] = "relax"
        user_state["energy_level"] = "low"
    elif any(word in lowered for word in ["stress", "overwhelmed", "anxious"]):
        user_state["mood"] = "stressed"
        user_state["viewing_intent"] = "escape"
        user_state["energy_level"] = "low"
    elif "bored" in lowered:
        user_state["mood"] = "bored"
        user_state["viewing_intent"] = "get_excited"
        user_state["energy_level"] = "medium"
    elif any(word in lowered for word in ["happy", "great", "good mood", "fun"]):
        user_state["mood"] = "happy"
        user_state["viewing_intent"] = "laugh"
        user_state["energy_level"] = "high"
    elif any(word in lowered for word in ["don't know", "do not know", "whatever"]):
        user_state["mood"] = "neutral"

    if any(word in lowered for word in ["light", "easy", "simple", "not heavy"]):
        user_state["content_complexity"] = "low"
    elif any(word in lowered for word in ["deep", "thought", "thoughtful", "complex"]):
        user_state["content_complexity"] = "high"

    if any(word in lowered for word in ["short", "quick", "not too long"]):
        user_state["preferred_length"] = "short"
    elif any(word in lowered for word in ["long", "epic", "binge"]):
        user_state["preferred_length"] = "long"

    if any(word in lowered for word in ["funny", "laugh", "comedy"]):
        user_state["viewing_intent"] = "laugh"
    elif any(word in lowered for word in ["comfort", "warm", "heartwarming"]):
        user_state["viewing_intent"] = "feel_comforted"
    elif any(word in lowered for word in ["exciting", "thrill", "adrenaline", "action"]):
        user_state["viewing_intent"] = "get_excited"
    elif any(word in lowered for word in ["escape", "switch off", "zone out"]):
        user_state["viewing_intent"] = "escape"
    elif any(word in lowered for word in ["relax", "calm", "chill"]):
        user_state["viewing_intent"] = "relax"

    if any(word in lowered for word in ["not heavy", "nothing heavy"]):
        user_state["avoid"].append("heavy")
    if "violent" in lowered:
        user_state["avoid"].append("violent")
    if "horror" in lowered:
        user_state["avoid"].append("horror")

    known_fields = [
        field
        for field in (
            "mood",
            "energy_level",
            "viewing_intent",
            "content_complexity",
            "preferred_length",
        )
        if user_state[field] != "unknown"
    ]

    confidence = 0.35 + (0.15 * len(known_fields))
    if _key_fields_known(user_state):
        confidence += 0.1
    if user_state["avoid"]:
        confidence += 0.05

    user_state["confidence"] = min(confidence, 0.95)
    return {
        "user_state": user_state,
    }


def analyze_user_state(
    message: str,
    max_follow_up_questions: int = MAX_RUNTIME_FOLLOW_UP_QUESTIONS,
) -> Dict[str, Any]:
    greeting_only = is_greeting_only_message(message)

    if not client:
        return _normalize_result(
            _heuristic_state(message),
            max_follow_up_questions,
            greeting_only=greeting_only,
        )

    system_prompt = load_prompt("analyze_user_state.txt")

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
        )
        content = response.choices[0].message.content.strip()
        parsed = safe_json_loads(content, DEFAULT_ANALYZER_RESULT)
        return _normalize_result(
            parsed,
            max_follow_up_questions,
            greeting_only=greeting_only,
        )
    except Exception as error:
        print(f"OpenAI analyzer error: {error}")
        return _normalize_result(
            _heuristic_state(message),
            max_follow_up_questions,
            greeting_only=greeting_only,
        )


def build_search_query_from_user_state(
    user_state: Dict[str, Any],
    original_text: str,
) -> Dict[str, Any]:
    query_parts: List[str] = []

    mood = user_state.get("mood")
    viewing_intent = user_state.get("viewing_intent")
    content_complexity = user_state.get("content_complexity")

    if mood and mood != "unknown":
        query_parts.append(mood)
    if viewing_intent and viewing_intent != "unknown":
        query_parts.append(viewing_intent.replace("_", " "))
    if content_complexity == "low":
        query_parts.append("light easy watch")
    elif content_complexity == "high":
        query_parts.append("deep thoughtful story")
    elif content_complexity == "medium":
        query_parts.append("balanced engaging story")

    for item in user_state.get("avoid", []):
        query_parts.append(f"not {item}")

    query_text = " ".join(query_parts).strip() or original_text

    return {
        "query_text": query_text,
        "release_year_min": None,
        "release_year_max": None,
        "duration_preference": (
            user_state.get("preferred_length")
            if user_state.get("preferred_length") in {"short", "medium", "long"}
            else None
        ),
        "target_audience": None,
        "age_category": None,
        "streaming": None,
        "type": None,
    }


class PendingConversationStore:
    def __init__(self) -> None:
        self._store: Dict[int, Dict[str, Any]] = {}

    def get(self, chat_id: int) -> Dict[str, Any] | None:
        return self._store.get(chat_id)

    def set(
        self,
        chat_id: int,
        original_message: str,
        conversation_messages: List[str],
        analysis: Dict[str, Any],
        follow_up_count: int,
        started_with_greeting: bool,
    ) -> None:
        self._store[chat_id] = {
            "original_message": original_message,
            "conversation_messages": conversation_messages,
            "analysis": analysis,
            "follow_up_count": follow_up_count,
            "started_with_greeting": started_with_greeting,
            "updated_at": time.time(),
        }

    def clear(self, chat_id: int) -> None:
        self._store.pop(chat_id, None)


def combine_conversation_messages(messages: List[str]) -> str:
    return "\n".join(
        f"User message {index}: {message}"
        for index, message in enumerate(messages, start=1)
    )
