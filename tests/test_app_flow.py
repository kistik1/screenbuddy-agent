import importlib

from fastapi.testclient import TestClient

from agent.conversation_state import ConversationSessionStore
from agent.screenbuddy_agent import ScreenBuddyAgent
from services import user_state_analyzer as analyzer


def _recommendation(title="Calm Movie"):
    return {
        "title": title,
        "genres": "Comedy, Family",
        "description": "Warm and comforting.",
        "type": "Movie",
        "release_year": "2024",
        "duration": "90 min",
        "target_audience": "adults",
        "age_category": "recent",
        "streaming": "Netflix",
        "similarity_score": 0.91,
        "cluster_id": "1",
        "cluster_name": "Comfort",
        "dbscan_cluster": "1",
        "is_outlier": False,
        "more_from_cluster": [],
    }


def _agent(search_calls):
    def fake_search(**kwargs):
        search_calls.append(kwargs["parsed_query"])
        return [_recommendation()]

    return ScreenBuddyAgent(
        store=ConversationSessionStore(),
        search_fn=fake_search,
        explanation_fn=lambda **kwargs: "This fits the easy comfort you described.",
        search_context={
            "df": object(),
            "vectorizer": object(),
            "tfidf_matrix": object(),
        },
    )


def test_agent_greeting_invites_natural_conversation(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(123, "Hello")

    assert response.message == "Hey, how are you? Want to watch something?"
    assert response.searched is False
    assert search_calls == []


def test_agent_discovery_asks_one_warm_follow_up(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(
        123,
        "Help me find something to watch",
    )

    assert response.message == (
        "I'd be happy to find something for you. How was your day today?"
    )
    assert response.searched is False
    assert search_calls == []


def test_agent_recommends_after_enough_context(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(
        123,
        "I had a long day and want something light and funny",
    )

    assert response.searched is True
    assert "Calm Movie" in response.message
    assert "Do these feel right" in response.message
    assert search_calls
    assert "tired" in search_calls[0]["query_text"]
    assert "funny" in search_calls[0]["query_text"]


def test_agent_negative_feedback_asks_refinement_without_restart(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "No, not it")

    assert response.message == (
        "Got it — was it too heavy, too boring, or just the wrong vibe?"
    )
    assert len(search_calls) == 1


def test_agent_feedback_with_direction_researches(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "I wanted something more fun")

    assert response.searched is True
    assert len(search_calls) == 2
    assert "funny and uplifting" in search_calls[1]["query_text"]
    assert "Do these feel right" in response.message


def test_agent_feedback_can_refine_to_tv_shows(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "only tv shows")

    assert response.searched is True
    assert len(search_calls) == 2
    assert search_calls[1]["type"] == "TV Show"


def test_agent_feedback_can_refine_to_movies(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "only movies")

    assert response.searched is True
    assert len(search_calls) == 2
    assert search_calls[1]["type"] == "Movie"


def test_agent_feedback_can_refine_existing_search_filters(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )

    refinements = (
        ("for adults", "target_audience", "adults"),
        ("something shorter", "duration_preference", "short"),
        ("netflix only", "streaming", "netflix"),
        ("after 2018", "release_year_min", 2018),
        ("before 2000", "release_year_max", 2000),
        ("make it classic", "age_category", "classic"),
    )

    for message, key, value in refinements:
        agent.handle_message(123, message)
        assert search_calls[-1][key] == value


def test_agent_feedback_keeps_previous_filters(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    agent.handle_message(123, "only tv shows")
    agent.handle_message(123, "make it shorter")

    assert search_calls[-1]["type"] == "TV Show"
    assert search_calls[-1]["duration_preference"] == "short"


def test_webhook_uses_agent_response(monkeypatch):
    app_module = importlib.import_module("app")
    app_module.screenbuddy_agent.reset(456)

    sent_messages = []

    monkeypatch.setattr(
        app_module.screenbuddy_agent,
        "handle_message",
        lambda chat_id, text: type(
            "Response",
            (),
            {"message": "Agent reply"},
        )(),
    )
    monkeypatch.setattr(
        app_module,
        "send_telegram_message",
        lambda chat_id, text: sent_messages.append((chat_id, text)) or True,
    )

    client = TestClient(app_module.app)
    response = client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 456},
                "text": "Hello",
            }
        },
    )

    assert response.status_code == 200
    assert sent_messages == [(456, "Agent reply")]
