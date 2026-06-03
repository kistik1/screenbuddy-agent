from types import SimpleNamespace

from agent import topic_router


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


def test_classify_message_topic_uses_llm_result(monkeypatch):
    monkeypatch.setattr(
        topic_router,
        "client",
        FakeClient(
            """
            {
              "classification": "off_topic",
              "reason": "travel advice"
            }
            """
        ),
    )

    result = topic_router.classify_message_topic(
        "What are Japan trip tips?"
    )

    assert result == "off_topic"


def test_classify_message_topic_falls_back_without_llm(monkeypatch):
    monkeypatch.setattr(topic_router, "client", None)

    result = topic_router.classify_message_topic(
        "What are Japan trip tips?"
    )

    assert result == "off_topic"
