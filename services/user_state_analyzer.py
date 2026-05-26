import time
from typing import Any, Dict, List

from services.llm_service import (
    OPENAI_MODEL,
    client,
    load_prompt,
    safe_json_loads,
)


MAX_RUNTIME_FOLLOW_UP_QUESTIONS = 2
MAX_ALLOWED_FOLLOW_UP_QUESTIONS = 3
FOLLOW_UP_THRESHOLD = 0.75
KEY_FIELDS = ("mood", "viewing_intent")

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

QUESTION_BANK = {
    "viewing_intent": "What are you in the mood for: comfort, laughs, or something exciting?",
    "mood": "How are you feeling right now: tired, bored, sad, or mostly neutral?",
    "preferred_length": "How much time do you have right now: short, medium, or long?",
    "content_complexity": "Do you want something light or something deeper?",
    "avoid": "Anything you definitely do not want to watch today?",
    "energy_level": "Do you want something calm, balanced, or high-energy?",
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


def _key_fields_known(user_state: Dict[str, Any]) -> bool:
    return all(user_state.get(field) != "unknown" for field in KEY_FIELDS)


def _calculate_missing_info(user_state: Dict[str, Any]) -> List[str]:
    priority = [
        "viewing_intent",
        "mood",
        "preferred_length",
        "content_complexity",
        "avoid",
        "energy_level",
    ]

    missing_info = _normalize_missing_info(
        user_state.get("missing_info")
    )

    for field in priority:
        value = user_state.get(field)
        if field == "avoid":
            if not value and field not in missing_info:
                missing_info.append(field)
            continue
        if value == "unknown" and field not in missing_info:
            missing_info.append(field)

    return missing_info


def _build_follow_up_questions(
    missing_info: List[str],
    max_questions: int,
) -> List[str]:
    cap = min(
        max_questions,
        MAX_RUNTIME_FOLLOW_UP_QUESTIONS,
        MAX_ALLOWED_FOLLOW_UP_QUESTIONS,
    )
    questions: List[str] = []
    for field in missing_info:
        question = QUESTION_BANK.get(field)
        if question and question not in questions:
            questions.append(question)
        if len(questions) >= cap:
            break
    return questions


def _normalize_result(
    raw_result: Dict[str, Any],
    max_follow_up_questions: int,
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

    needs_follow_up = (
        user_state["confidence"] < FOLLOW_UP_THRESHOLD
        or not _key_fields_known(user_state)
    )

    follow_up_questions = []
    if needs_follow_up:
        follow_up_questions = _build_follow_up_questions(
            user_state["missing_info"],
            max_follow_up_questions,
        )

    result["user_state"] = user_state
    result["needs_follow_up"] = bool(
        needs_follow_up and follow_up_questions
    )
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
    if not client:
        return _normalize_result(
            _heuristic_state(message),
            max_follow_up_questions,
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
        return _normalize_result(parsed, max_follow_up_questions)
    except Exception as error:
        print(f"OpenAI analyzer error: {error}")
        return _normalize_result(
            _heuristic_state(message),
            max_follow_up_questions,
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
    ) -> None:
        self._store[chat_id] = {
            "original_message": original_message,
            "conversation_messages": conversation_messages,
            "analysis": analysis,
            "updated_at": time.time(),
        }

    def clear(self, chat_id: int) -> None:
        self._store.pop(chat_id, None)


def combine_conversation_messages(messages: List[str]) -> str:
    return "\n".join(
        f"User message {index}: {message}"
        for index, message in enumerate(messages, start=1)
    )
