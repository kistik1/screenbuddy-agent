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
              "needs_follow_up": false,
              "assistant_reply": "",
              "follow_up_questions": []
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
    assert result["follow_up_questions"] == []


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
              "needs_follow_up": true,
              "assistant_reply": "What genre do you want?",
              "follow_up_questions": [
                "Q1",
                "Q2",
                "Q3"
              ]
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
    assert result["assistant_reply"] == (
        "Do you want something that lifts you up, distracts you, or just keeps you company?"
    )
    assert len(result["follow_up_questions"]) == 1
    assert result["follow_up_questions"][0].startswith(
        "Do you want something that lifts you up"
    )


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


def test_analyze_user_state_asks_one_human_question_for_tired_user(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state("I'm tired")

    assert result["needs_follow_up"] is True
    assert result["assistant_reply"] == (
        "Got it. Want something light and easy, or are you okay with something a bit deeper?"
    )
    assert result["follow_up_questions"] == [
        "Got it. Want something light and easy, or are you okay with something a bit deeper?"
    ]


def test_analyze_user_state_greeting_only_gets_warm_reply(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)

    result = analyzer.analyze_user_state("Hello!")

    assert result["needs_follow_up"] is True
    assert result["assistant_reply"] == (
        "Hey, how are you? Want to watch something?"
    )
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
              "needs_follow_up": false,
              "assistant_reply": "",
              "follow_up_questions": []
            }
            """
        ),
    )

    result = analyzer.analyze_user_state(
        "I'm tired and want something light and short"
    )

    assert result["needs_follow_up"] is False
    assert result["follow_up_questions"] == []


def test_build_search_query_from_user_state():
    search_query = (
        analyzer.build_search_query_from_user_state(
            user_state={
                "mood": "sad",
                "energy_level": "low",
                "viewing_intent": "feel_comforted",
                "content_complexity": "low",
                "preferred_length": "short",
                "avoid": ["violent"],
                "confidence": 0.8,
                "missing_info": [],
            },
            original_text="I feel sad, maybe something comforting",
        )
    )

    assert search_query["duration_preference"] == "short"
    assert "sad" in search_query["query_text"]
    assert "feel comforted" in search_query["query_text"]
    assert "not violent" in search_query["query_text"]
