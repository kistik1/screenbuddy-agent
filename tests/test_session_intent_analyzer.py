from types import SimpleNamespace

from services import session_intent_analyzer as analyzer


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=self.content,
                    )
                )
            ]
        )


class FakeClient:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


def test_analyze_follow_up_uses_structured_llm_result(monkeypatch):
    fake_client = FakeClient(
        """
        {
          "intent": "refine",
          "user_question": "",
          "question_type": "none",
          "refinements": {
            "streaming": "netflix",
            "duration_preference": "short",
            "ignored": "value"
          },
          "vibe_adjustment": {
            "desired_feeling": "funny and uplifting",
            "avoid_genres": ["heavy"]
          },
          "needs_clarification": false,
          "reason": "user asked to narrow the search"
        }
        """
    )
    monkeypatch.setattr(analyzer, "client", fake_client)

    result = analyzer.analyze_post_recommendation_follow_up(
        "Can you make it shorter and Netflix only?",
        "assistant recommended options",
        {"search_filters": {}},
    )

    assert result["intent"] == "refine"
    assert result["refinements"] == {
        "streaming": "netflix",
        "duration_preference": "short",
    }
    assert result["vibe_adjustment"] == {
        "desired_feeling": "funny and uplifting",
        "avoid_genres": ["heavy"],
    }
    assert result["needs_clarification"] is False
    assert fake_client.completions.kwargs["response_format"] == {
        "type": "json_object"
    }


def test_analyze_follow_up_preserves_question_intent(monkeypatch):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "intent": "ask_question",
              "user_question": "It is ok if I have only Netflix?",
              "question_type": "constraint_acceptability",
              "refinements": {"streaming": "netflix"},
              "vibe_adjustment": {},
              "needs_clarification": false,
              "reason": "user asks whether the constraint is acceptable"
            }
            """
        ),
    )

    result = analyzer.analyze_post_recommendation_follow_up(
        "It is ok if I have only Netflix?",
        "assistant recommended options",
    )

    assert result["intent"] == "ask_question"
    assert result["question_type"] == "constraint_acceptability"
    assert result["user_question"] == "It is ok if I have only Netflix?"


def test_analyze_follow_up_invalid_llm_result_is_ambiguous(monkeypatch):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "intent": "done",
              "question_type": "unsupported"
            }
            """
        ),
    )

    result = analyzer.analyze_post_recommendation_follow_up("ok")

    assert result["intent"] == "ambiguous"
    assert result["question_type"] == "none"
    assert result["needs_clarification"] is True


def test_analyze_follow_up_without_llm_returns_ambiguity(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)

    assert analyzer.analyze_post_recommendation_follow_up("ok") == {
        "intent": "ambiguous",
        "user_question": "",
        "question_type": "none",
        "refinements": {},
        "vibe_adjustment": {},
        "needs_clarification": True,
        "reason": "",
    }
