import importlib

from fastapi.testclient import TestClient


def test_webhook_sends_follow_up_and_stores_state(
    monkeypatch,
):
    app_module = importlib.import_module("app")
    app_module.conversation_store.clear(123)

    sent_messages = []

    monkeypatch.setattr(
        app_module,
        "analyze_user_state",
        lambda text: {
            "user_state": {
                "mood": "unknown",
                "energy_level": "unknown",
                "viewing_intent": "unknown",
                "content_complexity": "low",
                "preferred_length": "unknown",
                "avoid": [],
                "confidence": 0.4,
                "missing_info": [
                    "viewing_intent",
                    "preferred_length",
                ],
            },
            "needs_follow_up": True,
            "assistant_reply": (
                "Hello! What are you in the mood to watch tonight?"
            ),
            "follow_up_questions": [
                "What sounds better right now: something comforting, funny, or exciting?",
            ],
        },
    )
    monkeypatch.setattr(
        app_module,
        "send_telegram_message",
        lambda chat_id, text: sent_messages.append(
            (chat_id, text)
        )
        or True,
    )

    client = TestClient(app_module.app)
    response = client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 123},
                "text": "I don't know what to watch",
            }
        },
    )

    assert response.status_code == 200
    assert sent_messages
    assert (
        sent_messages[0][1]
        == "Hello! What are you in the mood to watch tonight?"
    )
    assert "I need a bit more to tune the recommendation" not in sent_messages[0][1]
    pending = app_module.conversation_store.get(123)
    assert pending is not None
    assert pending["conversation_messages"] == [
        "I don't know what to watch"
    ]
    assert pending["follow_up_count"] == 1


def test_webhook_resumes_flow_and_returns_recommendation(
    monkeypatch,
):
    app_module = importlib.import_module("app")
    app_module.conversation_store.clear(456)

    sent_messages = []
    calls = {"count": 0}

    def fake_analyzer(text):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "user_state": {
                    "mood": "unknown",
                    "energy_level": "unknown",
                    "viewing_intent": "unknown",
                    "content_complexity": "unknown",
                    "preferred_length": "unknown",
                    "avoid": [],
                    "confidence": 0.3,
                    "missing_info": [
                        "mood",
                        "viewing_intent",
                    ],
                },
                "needs_follow_up": True,
                "assistant_reply": (
                    "Hello! What are you in the mood to watch tonight?"
                ),
                "follow_up_questions": [
                    "What kind of mood are you in tonight?",
                ],
            }
        return {
            "user_state": {
                "mood": "sad",
                "energy_level": "low",
                "viewing_intent": "feel_comforted",
                "content_complexity": "low",
                "preferred_length": "short",
                "avoid": [],
                "confidence": 0.85,
                "missing_info": [],
                },
                "needs_follow_up": False,
                "assistant_reply": "",
                "follow_up_questions": [],
            }

    monkeypatch.setattr(
        app_module,
        "analyze_user_state",
        fake_analyzer,
    )
    monkeypatch.setattr(
        app_module,
        "build_search_query_from_user_state",
        lambda user_state, original_text: {
            "query_text": "sad feel comforted light easy watch",
            "release_year_min": None,
            "release_year_max": None,
            "duration_preference": "short",
            "target_audience": None,
            "age_category": None,
            "streaming": None,
            "type": None,
        },
    )
    monkeypatch.setattr(
        app_module,
        "search_titles",
        lambda **kwargs: [
            {
                "title": "Calm Movie",
                "genres": "Drama",
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
        ],
    )
    monkeypatch.setattr(
        app_module,
        "generate_recommendation_explanation",
        lambda **kwargs: "This should fit your mood.",
    )
    monkeypatch.setattr(
        app_module,
        "send_telegram_message",
        lambda chat_id, text: sent_messages.append(
            (chat_id, text)
        )
        or True,
    )

    client = TestClient(app_module.app)

    first = client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 456},
                "text": "Not sure what to watch",
            }
        },
    )
    second = client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 456},
                "text": "Something comforting and short",
            }
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(sent_messages) == 2
    assert sent_messages[0][1] == "Hello! What are you in the mood to watch tonight?"
    assert "ScreenBuddy Recommendations" in sent_messages[1][1]
    assert app_module.conversation_store.get(456) is None


def test_webhook_stops_after_three_follow_ups(
    monkeypatch,
):
    app_module = importlib.import_module("app")
    app_module.conversation_store.clear(789)

    sent_messages = []

    monkeypatch.setattr(
        app_module,
        "analyze_user_state",
        lambda text: {
            "user_state": {
                "mood": "unknown",
                "energy_level": "unknown",
                "viewing_intent": "unknown",
                "content_complexity": "unknown",
                "preferred_length": "unknown",
                "avoid": [],
                "confidence": 0.2,
                "missing_info": [
                    "mood",
                    "viewing_intent",
                ],
            },
            "needs_follow_up": True,
            "assistant_reply": "Hello! What are you in the mood to watch tonight?",
            "follow_up_questions": [
                "What kind of mood are you in tonight?",
            ],
        },
    )
    monkeypatch.setattr(
        app_module,
        "build_search_query_from_user_state",
        lambda user_state, original_text: {
            "query_text": original_text,
            "release_year_min": None,
            "release_year_max": None,
            "duration_preference": None,
            "target_audience": None,
            "age_category": None,
            "streaming": None,
            "type": None,
        },
    )
    monkeypatch.setattr(
        app_module,
        "search_titles",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        app_module,
        "generate_recommendation_explanation",
        lambda **kwargs: "",
    )
    monkeypatch.setattr(
        app_module,
        "send_telegram_message",
        lambda chat_id, text: sent_messages.append(
            (chat_id, text)
        )
        or True,
    )

    client = TestClient(app_module.app)
    client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 789},
                "text": "hey",
            }
        },
    )
    client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 789},
                "text": "still not sure",
            }
        },
    )
    client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 789},
                "text": "whatever works",
            }
        },
    )
    final_response = client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 789},
                "text": "anything",
            }
        },
    )

    assert final_response.status_code == 200
    assert len(sent_messages) == 4
    assert sent_messages[0][1] == "Hello! What are you in the mood to watch tonight?"
    assert sent_messages[1][1] == "Hello! What are you in the mood to watch tonight?"
    assert sent_messages[2][1] == "Hello! What are you in the mood to watch tonight?"
    assert "I could not find a strong enough match." in sent_messages[3][1]
    assert app_module.conversation_store.get(789) is None


def test_webhook_greeting_only_starts_intake(
    monkeypatch,
):
    app_module = importlib.import_module("app")
    app_module.conversation_store.clear(321)

    sent_messages = []

    monkeypatch.setattr(
        app_module,
        "analyze_user_state",
        lambda text: {
            "user_state": {
                "mood": "unknown",
                "energy_level": "unknown",
                "viewing_intent": "unknown",
                "content_complexity": "unknown",
                "preferred_length": "unknown",
                "avoid": [],
                "confidence": 0.0,
                "missing_info": [
                    "mood",
                    "viewing_intent",
                ],
            },
            "needs_follow_up": True,
            "assistant_reply": "Hello! What are you in the mood to watch tonight?",
            "follow_up_questions": [],
        },
    )
    monkeypatch.setattr(
        app_module,
        "send_telegram_message",
        lambda chat_id, text: sent_messages.append(
            (chat_id, text)
        )
        or True,
    )

    client = TestClient(app_module.app)
    response = client.post(
        "/webhook",
        json={
            "message": {
                "chat": {"id": 321},
                "text": "Hello!",
            }
        },
    )

    assert response.status_code == 200
    assert sent_messages == [
        (321, "Hello! What are you in the mood to watch tonight?")
    ]
    pending = app_module.conversation_store.get(321)
    assert pending is not None
    assert pending["started_with_greeting"] is True
    assert pending["follow_up_count"] == 1
