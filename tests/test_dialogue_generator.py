from agent import dialogue_generator
from agent.conversation_state import WatchSearchIntent
from agent.dialogue_generator import DialogueContext


def test_no_results_for_light_request_offers_concrete_fun_content_choices(
    monkeypatch,
):
    monkeypatch.setattr(dialogue_generator, "client", None)
    intent = WatchSearchIntent(
        intensity_tolerance="low",
        free_text_context="I want something light and not too long.",
    )

    message = dialogue_generator.generate_dialogue(
        DialogueContext(phase="no_results", intent=intent)
    )

    assert "stand-up" in message
    assert "comedy movie" in message
    assert "fun TV show" in message


def test_no_results_for_non_light_low_intensity_request_stays_general(
    monkeypatch,
):
    monkeypatch.setattr(dialogue_generator, "client", None)
    intent = WatchSearchIntent(
        intensity_tolerance="low",
        free_text_context="I want a documentary, nothing violent.",
    )

    message = dialogue_generator.generate_dialogue(
        DialogueContext(phase="no_results", intent=intent)
    )

    assert "stand-up" not in message
