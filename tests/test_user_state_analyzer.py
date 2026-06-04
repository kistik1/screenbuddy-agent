from types import SimpleNamespace

from services import user_state_analyzer as analyzer


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content

    def create(self, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=self.content
                    )
                )
            ]
        )


class FakeClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(
            completions=FakeCompletions(content)
        )


def test_analyze_user_state_skips_follow_up_when_confident(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "user_state": {
                "mood": "tired",
                "energy_level": "low",
                "viewing_intent": "relax",
                "content_complexity": "low",
                "preferred_length": "medium",
                "avoid": [],
                "confidence": 0.88,
                "missing_info": []
              },
              "needs_follow_up": false
            }
            """
        ),
    )

    result = analyzer.analyze_user_state(
        "I had a very exhausting day, I want something light"
    )

    assert result["user_state"]["mood"] == "tired"
    assert result["user_state"]["viewing_intent"] == "relax"
    assert result["needs_follow_up"] is False
    assert "follow_up_questions" not in result


def test_analyze_user_state_normalizes_and_limits_questions(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "user_state": {
                "mood": "mystery",
                "energy_level": "medium",
                "viewing_intent": "unknown",
                "content_complexity": "unknown",
                "preferred_length": "unknown",
                "avoid": "heavy",
                "confidence": 1.4,
                "missing_info": [
                  "viewing_intent",
                  "preferred_length",
                  "content_complexity",
                  "avoid"
                ]
              },
              "needs_follow_up": true
            }
            """
        ),
    )

    result = analyzer.analyze_user_state(
        "I don't know what to watch, just not something heavy",
        max_follow_up_questions=3,
    )

    assert result["user_state"]["mood"] == "unknown"
    assert result["user_state"]["confidence"] == 1.0
    assert result["user_state"]["avoid"] == ["heavy"]
    assert result["needs_follow_up"] is True
    assert result["user_state"]["missing_info"][0] == "viewing_intent"


def test_analyze_user_state_uses_heuristic_fallback(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)
    result = analyzer.analyze_user_state(
        "I'm bored and want something exciting"
    )

    assert result["user_state"]["mood"] == "bored"
    assert result["user_state"]["viewing_intent"] == "get_excited"
    assert result["user_state"]["energy_level"] == "medium"


def test_analyze_user_state_infers_drained_without_direct_tired_word(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state("I'm drained and my brain is off")

    assert result["user_state"]["mood"] == "tired"
    assert result["user_state"]["viewing_intent"] == "relax"
    assert result["user_state"]["energy_level"] == "low"


def test_analyze_user_state_infers_overwhelmed_escape(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state(
        "I'm overwhelmed and need to switch off"
    )

    assert result["user_state"]["mood"] == "stressed"
    assert result["user_state"]["viewing_intent"] == "escape"
    assert result["user_state"]["energy_level"] == "low"


def test_analyze_user_state_uncertain_user_still_needs_guidance(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state("I don't know what I want")

    assert result["needs_follow_up"] is True
    assert result["user_state"]["mood"] == "neutral"
    assert result["user_state"]["viewing_intent"] == "unknown"


def test_analyze_user_state_marks_tired_user_as_needing_follow_up(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state("I'm tired")

    assert result["needs_follow_up"] is True
    assert "content_complexity" in result["user_state"]["missing_info"]


def test_analyze_user_state_greeting_only_needs_follow_up(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state("Hello!")

    assert result["needs_follow_up"] is True
    assert result["user_state"]["mood"] == "unknown"


def test_analyze_user_state_does_not_require_avoid_question(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "user_state": {
                "mood": "tired",
                "energy_level": "low",
                "viewing_intent": "relax",
                "content_complexity": "low",
                "preferred_length": "short",
                "avoid": [],
                "confidence": 0.82,
                "missing_info": []
              },
              "needs_follow_up": false
            }
            """
        ),
    )

    result = analyzer.analyze_user_state(
        "I'm tired and want something light and short"
    )

    assert result["needs_follow_up"] is False
    assert "follow_up_questions" not in result
