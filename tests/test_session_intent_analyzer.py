from types import SimpleNamespace

from services import session_intent_analyzer as analyzer


class FakeCompletions:
    def __init__(self, content: str):
        self.content = content

    def create(self, **kwargs):
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
        self.chat = SimpleNamespace(
            completions=FakeCompletions(content),
        )


def test_classify_feedback_intent_uses_llm_result(monkeypatch):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "intent": "accepted",
              "reason": "user approves the recommendation"
            }
            """
        ),
    )

    result = analyzer.classify_feedback_intent(
        "ok",
        "assistant recommended options",
    )

    assert result == "accepted"


def test_classify_feedback_intent_invalid_llm_result_is_ambiguous(
    monkeypatch,
):
    monkeypatch.setattr(
        analyzer,
        "client",
        FakeClient(
            """
            {
              "intent": "done"
            }
            """
        ),
    )

    result = analyzer.classify_feedback_intent("ok")

    assert result == "ambiguous"


def test_classify_feedback_intent_falls_back_without_llm(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)

    assert analyzer.classify_feedback_intent("ok") == "accepted"
    assert analyzer.classify_feedback_intent("yes thanks") == "accepted"
    assert analyzer.classify_feedback_intent("not ok") == "negative"
    assert analyzer.classify_feedback_intent("only tv shows") == "refine"
    assert analyzer.classify_feedback_intent("more fun") == "refine"
