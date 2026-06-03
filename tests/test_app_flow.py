import importlib

from fastapi.testclient import TestClient

from agent.conversation_state import ConversationSessionStore
from agent.dialogue_generator import DialogueContext
from agent.screenbuddy_agent import ScreenBuddyAgent
from services import session_intent_analyzer
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


class FakeClock:
    def __init__(self, now=1_000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _agent(search_calls, recommendations=None, store=None):
    def fake_search(**kwargs):
        search_calls.append(kwargs["parsed_query"])
        if recommendations is None:
            return [_recommendation()]
        return recommendations

    def fake_dialogue(context: DialogueContext):
        if context.phase == "recommendations":
            titles = ", ".join(
                item["title"] for item in context.recommendations
            )
            return f"Try {titles}. Do these feel right?"
        if context.phase == "no_results":
            return "Generated no-results refinement?"
        if context.phase == "feedback_clarification":
            return "What felt off about them?"
        if context.phase == "off_topic":
            return "I am ScreenBuddy. Want help choosing a movie or show?"
        if context.phase == "greeting":
            return "Warm generated greeting?"
        if context.phase == "discovery_follow_up":
            return f"Generated follow-up for {context.follow_up_target}?"
        return f"Generated {context.phase}?"

    return ScreenBuddyAgent(
        store=store or ConversationSessionStore(),
        search_fn=fake_search,
        search_context={
            "df": object(),
            "vectorizer": object(),
            "tfidf_matrix": object(),
        },
        dialogue_fn=fake_dialogue,
    )


def test_session_store_reuses_session_before_timeout():
    clock = FakeClock()
    store = ConversationSessionStore(
        timeout_seconds=300,
        clock=clock,
    )

    session = store.get_or_create(123)
    clock.advance(299)

    assert store.get_or_create(123) is session


def test_session_store_expires_session_after_timeout():
    clock = FakeClock()
    store = ConversationSessionStore(
        timeout_seconds=300,
        clock=clock,
    )

    session = store.get_or_create(123)
    session.add_message("old context")
    store.set(session)
    clock.advance(301)
    fresh_session = store.get_or_create(123)

    assert fresh_session is not session
    assert fresh_session.messages == []


def test_session_store_invalid_timeout_uses_default():
    store = ConversationSessionStore(timeout_seconds=0)

    assert store.timeout_seconds == 300


def test_agent_greeting_invites_natural_conversation(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(123, "Hello")

    assert response.message == "Warm generated greeting?"
    assert response.searched is False
    assert search_calls == []


def test_agent_message_after_timeout_starts_fresh_session(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    clock = FakeClock()
    store = ConversationSessionStore(
        timeout_seconds=300,
        clock=clock,
    )
    agent = _agent(search_calls, store=store)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    clock.advance(301)
    response = agent.handle_message(123, "Hello")
    session = store.get(123)

    assert response.message == "Warm generated greeting?"
    assert session is not None
    assert session.messages == ["Hello"]


def test_agent_discovery_asks_one_warm_follow_up(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(
        123,
        "Help me find something to watch",
    )

    assert response.message == "Generated follow-up for viewing_intent?"
    assert response.searched is False
    assert search_calls == []


def test_agent_off_topic_redirects_without_search_or_session_message(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(123, "What are Japan trip tips?")
    session = agent.store.get(123)

    assert response.message == (
        "I am ScreenBuddy. Want help choosing a movie or show?"
    )
    assert response.searched is False
    assert search_calls == []
    assert session is not None
    assert session.messages == []


def test_agent_resumes_normally_after_off_topic_message(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(123, "What are Japan trip tips?")
    response = agent.handle_message(
        123,
        "I had a long day and want something light and funny",
    )

    assert response.searched is True
    assert "Calm Movie" in response.message
    assert search_calls


def test_agent_off_topic_while_awaiting_feedback_preserves_feedback_state(
    monkeypatch,
):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "What are Japan trip tips?")
    session = agent.store.get(123)

    assert response.searched is False
    assert session is not None
    assert session.awaiting_feedback is True
    assert len(search_calls) == 1


def test_agent_unclear_topic_uses_normal_discovery_flow(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(123, "I do not know")

    assert response.message == "Generated follow-up for viewing_intent?"
    assert response.searched is False
    assert search_calls == []


def test_agent_watch_related_japan_message_stays_in_scope(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    response = agent.handle_message(123, "What should I watch in Japan?")

    assert response.searched is False
    assert response.message == "Generated follow-up for viewing_intent?"
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


def test_agent_no_results_asks_generated_refinement(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls, recommendations=[])

    response = agent.handle_message(
        123,
        "I had a long day and want something light and funny",
    )
    session = agent.store.get(123)

    assert response.searched is True
    assert response.message == "Generated no-results refinement?"
    assert session is not None
    assert session.awaiting_feedback is False


def test_agent_negative_feedback_asks_refinement_without_restart(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    monkeypatch.setattr(session_intent_analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "No, not it")

    assert response.message == "What felt off about them?"
    assert len(search_calls) == 1


def test_agent_accepts_feedback_and_ends_session(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    monkeypatch.setattr(session_intent_analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    response = agent.handle_message(123, "ok")

    assert response.message == "Good watching time."
    assert response.searched is False
    assert len(search_calls) == 1
    assert agent.store.get(123) is None


def test_agent_starts_fresh_after_feedback_acceptance(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    monkeypatch.setattr(session_intent_analyzer, "client", None)
    search_calls = []
    agent = _agent(search_calls)

    agent.handle_message(
        123,
        "I had a long day and want something light",
    )
    agent.handle_message(123, "yes thanks")
    response = agent.handle_message(123, "Hello")
    session = agent.store.get(123)

    assert response.message == "Warm generated greeting?"
    assert session is not None
    assert session.messages == ["Hello"]


def test_agent_feedback_with_direction_researches(monkeypatch):
    monkeypatch.setattr(analyzer, "client", None)
    monkeypatch.setattr(session_intent_analyzer, "client", None)
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


def test_webhook_start_resets_session_and_sends_onboarding(monkeypatch):
    app_module = importlib.import_module("app")
    app_module.screenbuddy_agent.store.get_or_create(456).add_message(
        "old message"
    )

    sent_messages = []

    monkeypatch.setattr(
        app_module,
        "generate_dialogue",
        lambda context: f"Generated {context.phase}",
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
                "text": "/start",
            }
        },
    )

    assert response.status_code == 200
    assert sent_messages == [(456, "Generated greeting")]
    assert app_module.screenbuddy_agent.store.get(456) is None


def test_webhook_new_resets_session_and_sends_new_session_copy(
    monkeypatch,
):
    app_module = importlib.import_module("app")
    app_module.screenbuddy_agent.store.get_or_create(456).add_message(
        "old message"
    )

    sent_messages = []

    monkeypatch.setattr(
        app_module,
        "generate_dialogue",
        lambda context: f"Generated {context.phase}",
    )
    monkeypatch.setattr(
        app_module.screenbuddy_agent,
        "handle_message",
        lambda chat_id, text: (_ for _ in ()).throw(
            AssertionError("handle_message should not run for /new")
        ),
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
                "text": "/new",
            }
        },
    )

    assert response.status_code == 200
    assert sent_messages == [(456, "Generated session_reset")]
    assert app_module.screenbuddy_agent.store.get(456) is None


def test_webhook_help_skips_agent_and_preserves_session(monkeypatch):
    app_module = importlib.import_module("app")
    session = app_module.screenbuddy_agent.store.get_or_create(456)
    session.add_message("keep me")
    session.updated_at = 0

    sent_messages = []

    monkeypatch.setattr(
        app_module,
        "generate_dialogue",
        lambda context: f"Generated {context.phase}",
    )
    monkeypatch.setattr(
        app_module.screenbuddy_agent,
        "handle_message",
        lambda chat_id, text: (_ for _ in ()).throw(
            AssertionError("handle_message should not run for /help")
        ),
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
                "text": "/help",
            }
        },
    )

    assert response.status_code == 200
    assert sent_messages == [(456, "Generated help")]
    assert app_module.screenbuddy_agent.store.get(456) is session
    assert session.messages == ["keep me"]


def test_session_timeout_env_parser_falls_back_for_invalid_values(
    monkeypatch,
):
    app_module = importlib.import_module("app")

    monkeypatch.setenv("SCREENBUDDY_SESSION_TIMEOUT_SECONDS", "nope")
    assert app_module._session_timeout_seconds() == 300

    monkeypatch.setenv("SCREENBUDDY_SESSION_TIMEOUT_SECONDS", "0")
    assert app_module._session_timeout_seconds() == 300

    monkeypatch.setenv("SCREENBUDDY_SESSION_TIMEOUT_SECONDS", "120")
    assert app_module._session_timeout_seconds() == 120

