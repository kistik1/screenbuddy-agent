from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


EnergyLevel = Literal["low", "medium", "high", "unknown"]
IntensityTolerance = Literal["low", "medium", "high", "unknown"]


@dataclass
class UserPreferenceState:
    current_mood: str = "unknown"
    desired_feeling: str = "unknown"
    energy_level: EnergyLevel = "unknown"
    intensity_tolerance: IntensityTolerance = "unknown"
    genres: List[str] = field(default_factory=list)
    avoid_genres: List[str] = field(default_factory=list)
    runtime_preference: str = "unknown"
    language_preference: str = "unknown"
    platform_preference: str = "unknown"
    free_text_context: str = ""
    confidence: float = 0.0

    def merge(self, other: "UserPreferenceState") -> None:
        for field_name in (
            "current_mood",
            "desired_feeling",
            "energy_level",
            "intensity_tolerance",
            "runtime_preference",
            "language_preference",
            "platform_preference",
        ):
            incoming = getattr(other, field_name)
            if incoming != "unknown":
                setattr(self, field_name, incoming)

        self.genres = _merge_unique(self.genres, other.genres)
        self.avoid_genres = _merge_unique(
            self.avoid_genres,
            other.avoid_genres,
        )
        if other.free_text_context:
            self.free_text_context = other.free_text_context
        self.confidence = max(self.confidence, other.confidence)

    def has_emotional_signal(self) -> bool:
        return (
            self.current_mood != "unknown"
            or self.desired_feeling != "unknown"
        )

    def has_directional_signal(self) -> bool:
        return any(
            [
                self.energy_level != "unknown",
                self.intensity_tolerance != "unknown",
                self.runtime_preference != "unknown",
                self.language_preference != "unknown",
                self.platform_preference != "unknown",
                bool(self.genres),
                bool(self.avoid_genres),
            ]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_mood": self.current_mood,
            "desired_feeling": self.desired_feeling,
            "energy_level": self.energy_level,
            "intensity_tolerance": self.intensity_tolerance,
            "genres": self.genres,
            "avoid_genres": self.avoid_genres,
            "runtime_preference": self.runtime_preference,
            "language_preference": self.language_preference,
            "platform_preference": self.platform_preference,
            "free_text_context": self.free_text_context,
            "confidence": self.confidence,
        }


@dataclass
class WatchSearchIntent:
    desired_feeling: Optional[str] = None
    current_mood: Optional[str] = None
    energy_level: Optional[str] = None
    intensity_tolerance: Optional[str] = None
    genres: List[str] = field(default_factory=list)
    avoid_genres: List[str] = field(default_factory=list)
    runtime_preference: Optional[str] = None
    language_preference: Optional[str] = None
    platform_preference: Optional[str] = None
    free_text_context: str = ""

    def to_search_query(self) -> Dict[str, Any]:
        query_parts: List[str] = []
        for value in (
            self.current_mood,
            self.desired_feeling,
            self.energy_level,
            self.intensity_tolerance,
            self.free_text_context,
        ):
            if value:
                query_parts.append(value.replace("_", " "))
        query_parts.extend(self.genres)
        query_parts.extend(f"not {item}" for item in self.avoid_genres)

        return {
            "query_text": " ".join(query_parts).strip()
            or self.free_text_context,
            "release_year_min": None,
            "release_year_max": None,
            "duration_preference": self.runtime_preference,
            "target_audience": None,
            "age_category": None,
            "streaming": self.platform_preference,
            "type": None,
        }


@dataclass
class ConversationSession:
    chat_id: int
    messages: List[str] = field(default_factory=list)
    user_state: UserPreferenceState = field(
        default_factory=UserPreferenceState
    )
    follow_up_count: int = 0
    last_intent: Optional[WatchSearchIntent] = None
    last_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    awaiting_feedback: bool = False
    updated_at: float = field(default_factory=time.time)

    def add_message(self, message: str) -> None:
        self.messages.append(message)
        self.updated_at = time.time()

    def conversation_text(self) -> str:
        return "\n".join(
            f"User message {index}: {message}"
            for index, message in enumerate(self.messages, start=1)
        )


class ConversationSessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[int, ConversationSession] = {}

    def get_or_create(self, chat_id: int) -> ConversationSession:
        if chat_id not in self._sessions:
            self._sessions[chat_id] = ConversationSession(chat_id=chat_id)
        return self._sessions[chat_id]

    def get(self, chat_id: int) -> Optional[ConversationSession]:
        return self._sessions.get(chat_id)

    def set(self, session: ConversationSession) -> None:
        session.updated_at = time.time()
        self._sessions[session.chat_id] = session

    def clear(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)


def _merge_unique(existing: List[str], incoming: List[str]) -> List[str]:
    result = list(existing)
    for item in incoming:
        normalized = item.strip().lower()
        if normalized and normalized not in result:
            result.append(normalized)
    return result

