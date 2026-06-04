from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any


@dataclass(frozen=True)
class TurnExpectation:
    action: str
    contains: tuple[str, ...] = ()
    contains_any: tuple[str, ...] = ()
    not_contains: tuple[str, ...] = ()
    searched: bool | None = None
    intent: dict[str, Any] = field(default_factory=dict)
    search: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Flow:
    id: str
    summary: str
    user_inputs: tuple[str, ...]
    expectations: tuple[TurnExpectation, ...]
    project_fix_recommendation: str
    issue_key: str


FLOWS: tuple[Flow, ...] = (
    Flow(
        id="regular_greeting",
        summary="Greeting starts a warm watch conversation.",
        user_inputs=("Hello",),
        expectations=(
            TurnExpectation(
                action="ask_follow_up",
                contains=("Want to watch something",),
                searched=False,
            ),
        ),
        project_fix_recommendation=(
            "Keep greetings focused on inviting the user into a watch choice "
            "instead of searching immediately."
        ),
        issue_key="onboarding",
    ),
    Flow(
        id="regular_vague_request",
        summary="Vague watch request asks one human follow-up.",
        user_inputs=("Can you help me find something to watch?",),
        expectations=(
            TurnExpectation(
                action="ask_follow_up",
                contains=("How was your day",),
                searched=False,
            ),
        ),
        project_fix_recommendation=(
            "Tune the discovery policy to ask one lightweight emotional "
            "question before recommending from vague requests."
        ),
        issue_key="discovery",
    ),
    Flow(
        id="main_goal_drained_inferred_state",
        summary="Drained user state is inferred without direct tired wording.",
        user_inputs=("I'm drained and my brain is off",),
        expectations=(
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                search={"query_text_contains": ("tired", "easy comfort")},
            ),
        ),
        project_fix_recommendation=(
            "Treat indirect state language as the main recommendation signal, "
            "not only explicit mood words like happy or sad."
        ),
        issue_key="main_goal",
    ),
    Flow(
        id="main_goal_overwhelmed_escape",
        summary="Overwhelmed user gets an escape-oriented recommendation.",
        user_inputs=("I'm overwhelmed and need to switch off",),
        expectations=(
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                search={"query_text_contains": ("stressed", "escape")},
            ),
        ),
        project_fix_recommendation=(
            "Infer user state from natural language such as overwhelmed or "
            "switch off and carry that state into search."
        ),
        issue_key="main_goal",
    ),
    Flow(
        id="main_goal_uncertain_guided_options",
        summary="Uncertain user gets guided options before recommendations.",
        user_inputs=(
            "I feel blank and don't know what I want",
            "Something easygoing and short",
        ),
        expectations=(
            TurnExpectation(
                action="ask_follow_up",
                contains_any=(
                    "easygoing",
                    "absorbing",
                    "quick watch",
                    "settle into",
                    "switch off",
                    "cozy",
                    "laugh",
                    "exciting",
                    "lighter",
                    "funnier",
                    "cozier",
                    "more exciting",
                ),
                searched=False,
            ),
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                search={
                    "query_text_contains": ("easygoing", "short"),
                    "duration_preference": "short",
                },
            ),
        ),
        project_fix_recommendation=(
            "When the user does not know what they want, ask a guided "
            "choice-style question and use the answer to recommend."
        ),
        issue_key="main_goal",
    ),
    Flow(
        id="regular_tired_light",
        summary="Tired and light request produces easy recommendations.",
        user_inputs=("I had a long day and want something light and funny",),
        expectations=(
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                search={"query_text_contains": ("tired", "funny")},
            ),
        ),
        project_fix_recommendation=(
            "Improve state extraction for tired/light/funny language and "
            "ensure the search intent carries those signals."
        ),
        issue_key="intent_extraction",
    ),
    Flow(
        id="regular_bored_exciting",
        summary="Bored user asking for excitement gets an energetic direction.",
        user_inputs=("I'm bored and want something exciting tonight",),
        expectations=(
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                search={"query_text_contains": ("bored", "exciting")},
            ),
        ),
        project_fix_recommendation=(
            "Map boredom and excitement into a stronger search query and "
            "ranking reason."
        ),
        issue_key="intent_extraction",
    ),
    Flow(
        id="regular_sad_comfort",
        summary="Sad user looking for comfort gets gentle recommendations.",
        user_inputs=("I feel sad and need something comforting",),
        expectations=(
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                search={"query_text_contains": ("sad", "comfort")},
            ),
        ),
        project_fix_recommendation=(
            "Strengthen comfort-seeking extraction so sad users receive "
            "gentle, emotionally aligned options."
        ),
        issue_key="intent_extraction",
    ),
    Flow(
        id="regular_comedy",
        summary="Comedy request preserves genre preference.",
        user_inputs=("I want a comedy that feels playful",),
        expectations=(
            TurnExpectation(
                action="recommend",
                contains=("Do these feel right",),
                searched=True,
                intent={"genres": ("comedy",)},
            ),
        ),
        project_fix_recommendation=(
            "Preserve explicit genre requests in the search intent and ranking."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_short",
        summary="Short runtime request reaches search filters.",
        user_inputs=("I'm tired and want something short and easy",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"duration_preference": "short"},
            ),
        ),
        project_fix_recommendation=(
            "Extract short/quick runtime language into the duration filter."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_kids",
        summary="Kids/family viewing request gets a family-safe filter.",
        user_inputs=("We need something light for kids after dinner",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"target_audience": "kids"},
            ),
        ),
        project_fix_recommendation=(
            "Support audience filters during initial discovery, not only "
            "post-recommendation feedback."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_family",
        summary="Family viewing request keeps family audience.",
        user_inputs=("Find a warm family movie for tonight",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"target_audience": "family", "type": "Movie"},
            ),
        ),
        project_fix_recommendation=(
            "Treat family and movie words as first-turn search filters."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_adults",
        summary="Adults-only preference reaches search filters.",
        user_inputs=("I want something thoughtful for adults",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"target_audience": "adults"},
            ),
        ),
        project_fix_recommendation=(
            "Extract adult audience preferences before recommendation."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_tv_only",
        summary="TV-only initial request uses TV Show filter.",
        user_inputs=("I'm bored, only TV shows please",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"type": "TV Show"},
            ),
        ),
        project_fix_recommendation=(
            "Apply content-type filters from first-turn messages."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_movie_only",
        summary="Movie-only initial request uses Movie filter.",
        user_inputs=("I'm tired, only movies please",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"type": "Movie"},
            ),
        ),
        project_fix_recommendation=(
            "Apply movie-only filters before the first recommendation."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_classic",
        summary="Classic preference reaches age category.",
        user_inputs=("I want a classic cozy movie",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"age_category": "classic", "type": "Movie"},
            ),
        ),
        project_fix_recommendation=(
            "Extract classic/older age preferences during initial discovery."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_recent",
        summary="Recent preference reaches age category.",
        user_inputs=("I'm bored and want something recent and fun",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"age_category": "recent"},
            ),
        ),
        project_fix_recommendation=(
            "Extract recent/latest/newer language into age filters."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_avoid_horror",
        summary="Avoid-horror request carries avoid genre.",
        user_inputs=("I want something relaxing, no horror",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                intent={"avoid_genres": ("horror",)},
            ),
        ),
        project_fix_recommendation=(
            "Ensure avoidances stay in user state and influence ranking."
        ),
        issue_key="avoidances",
    ),
    Flow(
        id="regular_avoid_heavy",
        summary="Avoid-heavy request keeps low intensity.",
        user_inputs=("I feel fragile, not something heavy",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                intent={"intensity_tolerance": "low"},
            ),
        ),
        project_fix_recommendation=(
            "Convert heavy-content avoidance into low intensity tolerance."
        ),
        issue_key="avoidances",
    ),
    Flow(
        id="regular_romance",
        summary="Romance genre is preserved.",
        user_inputs=("I want a sweet romance that is easy to watch",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                intent={"genres": ("romance",)},
            ),
        ),
        project_fix_recommendation=(
            "Preserve romance as an explicit genre in the intent."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_thriller",
        summary="High-energy thriller request preserves genre.",
        user_inputs=("Give me a tense thriller, my brain is awake",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                intent={"genres": ("thriller",)},
            ),
        ),
        project_fix_recommendation=(
            "Preserve thriller and higher-intensity cues without over-softening."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_documentary",
        summary="Documentary request preserves genre.",
        user_inputs=("I want a thoughtful documentary tonight",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                intent={"genres": ("documentary",)},
            ),
        ),
        project_fix_recommendation=(
            "Preserve documentary as a direct genre signal."
        ),
        issue_key="filters",
    ),
    Flow(
        id="regular_language",
        summary="Language preference should be retained.",
        user_inputs=("I want something relaxing in Spanish",),
        expectations=(
            TurnExpectation(
                action="recommend",
                searched=True,
                intent={"language_preference": "spanish"},
            ),
        ),
        project_fix_recommendation=(
            "Add language extraction so language preferences affect search."
        ),
        issue_key="filters",
    ),
    Flow(
        id="irrelevant_weather_first",
        summary="Irrelevant weather question should not trigger a watch search.",
        user_inputs=("What is the weather tomorrow?",),
        expectations=(
            TurnExpectation(
                action="redirect",
                searched=False,
                not_contains=("I found a few", "Do these feel right"),
            ),
        ),
        project_fix_recommendation=(
            "Detect off-topic questions and briefly redirect back to watch "
            "recommendations instead of consuming follow-up budget."
        ),
        issue_key="off_topic",
    ),
    Flow(
        id="irrelevant_news_first",
        summary="Current-news question should be redirected.",
        user_inputs=("What happened in the news today?",),
        expectations=(
            TurnExpectation(
                action="redirect",
                searched=False,
                not_contains=("I found a few", "Do these feel right"),
            ),
        ),
        project_fix_recommendation=(
            "Add an off-topic guard for non-entertainment informational "
            "questions."
        ),
        issue_key="off_topic",
    ),
    Flow(
        id="irrelevant_math_first",
        summary="Random math question should not become recommendation context.",
        user_inputs=("Can you calculate 18 times 42?",),
        expectations=(
            TurnExpectation(
                action="redirect",
                searched=False,
                not_contains=("I found a few", "Do these feel right"),
            ),
        ),
        project_fix_recommendation=(
            "Separate unrelated utility questions from watch-intent discovery."
        ),
        issue_key="off_topic",
    ),
    Flow(
        id="irrelevant_smalltalk_first",
        summary="Small talk should be handled without searching.",
        user_inputs=("Do you like pizza?",),
        expectations=(
            TurnExpectation(
                action="redirect",
                searched=False,
                not_contains=("I found a few",),
            ),
        ),
        project_fix_recommendation=(
            "Handle casual off-topic small talk with a short redirect."
        ),
        issue_key="off_topic",
    ),
    Flow(
        id="irrelevant_after_recommendation",
        summary="Off-topic question after recommendations should not re-search.",
        user_inputs=(
            "I had a long day and want something light",
            "What is the weather tomorrow?",
        ),
        expectations=(
            TurnExpectation(action="recommend", searched=True),
            TurnExpectation(
                action="redirect",
                searched=False,
                not_contains=("I found a few",),
            ),
        ),
        project_fix_recommendation=(
            "When awaiting feedback, classify unrelated questions before "
            "reusing prior recommendation state."
        ),
        issue_key="off_topic",
    ),
    Flow(
        id="approval_accepts_final",
        summary="User approval should close the recommendation loop.",
        user_inputs=(
            "I had a long day and want something light and funny",
            "Yes, these feel right",
        ),
        expectations=(
            TurnExpectation(action="recommend", searched=True),
            TurnExpectation(
                action="accept",
                searched=False,
                not_contains=("I found a few", "Do these feel right"),
            ),
        ),
        project_fix_recommendation=(
            "Add positive-feedback handling so acceptance does not trigger a "
            "new search or another tuning prompt."
        ),
        issue_key="feedback",
    ),
    Flow(
        id="approval_pick_one",
        summary="User choosing a recommendation should be acknowledged.",
        user_inputs=(
            "I'm sad and want something comforting",
            "The first one sounds good",
        ),
        expectations=(
            TurnExpectation(action="recommend", searched=True),
            TurnExpectation(
                action="accept",
                searched=False,
                not_contains=("I found a few",),
            ),
        ),
        project_fix_recommendation=(
            "Treat explicit selection of a recommended title as acceptance."
        ),
        issue_key="feedback",
    ),
    Flow(
        id="bad_recommendation_plain",
        summary="Bad recommendation feedback should ask for refinement.",
        user_inputs=(
            "I want something relaxing and funny",
            "That is a bad recommendation",
        ),
        expectations=(
            TurnExpectation(action="recommend", searched=True),
            TurnExpectation(
                action="ask_refinement",
                searched=False,
                contains=("wrong vibe",),
            ),
        ),
        project_fix_recommendation=(
            "Expand negative-feedback detection to include bad recommendation "
            "language."
        ),
        issue_key="feedback",
    ),
    Flow(
        id="bad_recommendation_wrong_vibe",
        summary="Wrong-vibe feedback should ask a refinement question.",
        user_inputs=(
            "I am bored and want something exciting",
            "Wrong vibe, not what I wanted",
        ),
        expectations=(
            TurnExpectation(action="recommend", searched=True),
            TurnExpectation(
                action="ask_refinement",
                searched=False,
                contains=("too heavy", "too boring", "wrong vibe"),
            ),
        ),
        project_fix_recommendation=(
            "Keep negative feedback in refinement mode instead of restarting "
            "discovery."
        ),
        issue_key="feedback",
    ),
    Flow(
        id="change_final_netflix_only",
        summary="Final recommendation can be changed to Netflix only.",
        user_inputs=(
            "I had a long day and want something light and funny",
            "Netflix only",
        ),
        expectations=(
            TurnExpectation(action="recommend", searched=True),
            TurnExpectation(
                action="recommend",
                searched=True,
                search={"streaming": "netflix"},
            ),
        ),
        project_fix_recommendation=(
            "Keep post-recommendation platform refinements and re-run search "
            "with the requested streaming filter."
        ),
        issue_key="feedback_filters",
    ),
)


def build_flow_batch(*, count: int, seed: int) -> tuple[Flow, ...]:
    if count < 1:
        raise ValueError("count must be at least 1")

    rng = random.Random(seed)
    generated = list(_generated_flow_candidates())
    rng.shuffle(generated)

    if count < len(FLOWS):
        baseline = list(FLOWS)
        rng.shuffle(baseline)
        return tuple(baseline[:count])

    selected = list(FLOWS)
    generated_index = 0
    generation_round = 1
    while len(selected) < count:
        if generated_index == len(generated):
            generation_round += 1
            generated_index = 0
            rng.shuffle(generated)

        flow = generated[generated_index]
        generated_index += 1
        if generation_round > 1:
            flow = _copy_flow_with_id(
                flow,
                f"{flow.id}_repeat_{generation_round}",
            )
        selected.append(flow)

    return tuple(selected)


def _generated_flow_candidates() -> tuple[Flow, ...]:
    flows: list[Flow] = []
    flows.extend(_preference_combination_flows())
    flows.extend(_language_flows())
    flows.extend(_avoidance_flows())
    flows.extend(_feedback_refinement_flows())
    flows.extend(_off_topic_flows())
    return tuple(flows)


def _preference_combination_flows() -> list[Flow]:
    moods = (
        ("tired", "I'm tired", ("tired",)),
        ("bored", "I'm bored", ("bored",)),
        ("sad", "I feel sad", ("sad",)),
        ("stressed", "I'm stressed", ("stressed", "escape")),
        ("happy", "I'm in a good mood", ("happy", "funny")),
    )
    genres = (
        "action",
        "animation",
        "comedy",
        "documentary",
        "drama",
        "romance",
        "sci-fi",
        "thriller",
    )
    durations = (
        ("short", "short"),
        ("medium", "normal length"),
        ("long", "long"),
    )
    content_types = (
        ("movie", "movie", "Movie"),
        ("tv_show", "TV show", "TV Show"),
    )
    audiences = (
        ("kids", "kids", "kids"),
        ("family", "family", "family"),
        ("teens", "teens", "teens"),
        ("adults", "adults", "adults"),
    )
    platforms = (
        ("netflix", "Netflix", "netflix"),
        ("hulu", "Hulu", "hulu"),
        ("disney", "Disney+", "disney"),
        ("hbo", "Max", "hbo"),
        ("apple", "Apple TV+", "apple"),
        ("amazon_prime", "Prime Video", "amazon prime"),
    )
    ages = (
        ("classic", "classic", "classic"),
        ("recent", "recent", "recent"),
        ("modern", "modern", "modern"),
    )

    flows: list[Flow] = []
    for mood_id, mood_text, query_terms in moods:
        for genre in genres:
            for duration_id, duration_text in durations:
                for type_id, type_text, expected_type in content_types:
                    for audience_id, audience_text, expected_audience in audiences:
                        for platform_id, platform_text, expected_platform in platforms:
                            for age_id, age_text, expected_age in ages:
                                flow_id = "_".join(
                                    (
                                        "generated",
                                        mood_id,
                                        duration_id,
                                        platform_id,
                                        type_id,
                                        audience_id,
                                        genre.replace("-", "_"),
                                        age_id,
                                    )
                                )
                                message = (
                                    f"{mood_text} and want a light {duration_text} "
                                    f"{age_text} {genre} {type_text} for "
                                    f"{audience_text} on {platform_text}."
                                )
                                flows.append(
                                    Flow(
                                        id=flow_id,
                                        summary=(
                                            "Generated first-turn preference "
                                            "request preserves mood, genre, "
                                            "platform, type, audience, length, "
                                            "and age filters."
                                        ),
                                        user_inputs=(message,),
                                        expectations=(
                                            TurnExpectation(
                                                action="recommend",
                                                contains=("Do these feel right",),
                                                searched=True,
                                                intent={"genres": (genre,)},
                                                search={
                                                    "query_text_contains": query_terms,
                                                    "duration_preference": duration_id,
                                                    "type": expected_type,
                                                    "target_audience": expected_audience,
                                                    "streaming": expected_platform,
                                                    "age_category": expected_age,
                                                },
                                            ),
                                        ),
                                        project_fix_recommendation=(
                                            "Preserve explicit first-turn filters "
                                            "when building the search intent."
                                        ),
                                        issue_key="filters",
                                    )
                                )
    return flows


def _language_flows() -> list[Flow]:
    languages = (
        ("spanish", "Spanish"),
        ("french", "French"),
        ("korean", "Korean"),
        ("japanese", "Japanese"),
    )
    return [
        Flow(
            id=f"generated_language_{language_id}",
            summary="Generated language preference should be retained.",
            user_inputs=(f"I am tired and want something relaxing in {label}.",),
            expectations=(
                TurnExpectation(
                    action="recommend",
                    contains=("Do these feel right",),
                    searched=True,
                    intent={"language_preference": language_id},
                ),
            ),
            project_fix_recommendation=(
                "Extract language preferences so they affect recommendation "
                "state and search."
            ),
            issue_key="filters",
        )
        for language_id, label in languages
    ]


def _avoidance_flows() -> list[Flow]:
    cases = (
        ("horror", "I am stressed and want a light comedy movie, no horror.", "horror"),
        ("violent", "I feel sad and want a warm movie, nothing violent.", "violent"),
        ("heavy", "I am tired and want a short comedy, nothing heavy.", "heavy"),
    )
    return [
        Flow(
            id=f"generated_avoid_{case_id}",
            summary="Generated avoidance request carries negative preference.",
            user_inputs=(message,),
            expectations=(
                TurnExpectation(
                    action="recommend",
                    contains=("Do these feel right",),
                    searched=True,
                    intent={"avoid_genres": (expected,)},
                ),
            ),
            project_fix_recommendation=(
                "Ensure avoidances stay in user state and influence ranking."
            ),
            issue_key="avoidances",
        )
        for case_id, message, expected in cases
    ]


def _feedback_refinement_flows() -> list[Flow]:
    first_turn = "I had a long day and want something light and funny"
    refinements = (
        ("tv_show", "only TV shows", {"type": "TV Show"}),
        ("movie", "only movies", {"type": "Movie"}),
        ("short", "make it shorter", {"duration_preference": "short"}),
        ("long", "make it longer", {"duration_preference": "long"}),
        ("netflix", "Netflix only", {"streaming": "netflix"}),
        ("classic", "make it classic", {"age_category": "classic"}),
        ("after_2018", "after 2018", {"release_year_min": 2018}),
        ("before_2000", "before 2000", {"release_year_max": 2000}),
        ("adults", "for adults", {"target_audience": "adults"}),
        ("family", "for family", {"target_audience": "family"}),
    )
    flows: list[Flow] = []
    for refinement_id, message, search in refinements:
        flows.append(
            Flow(
                id=f"generated_feedback_{refinement_id}",
                summary="Generated feedback refinement updates search filters.",
                user_inputs=(first_turn, message),
                expectations=(
                    TurnExpectation(action="recommend", searched=True),
                    TurnExpectation(
                        action="recommend",
                        contains=("Do these feel right",),
                        searched=True,
                        search=search,
                    ),
                ),
                project_fix_recommendation=(
                    "Keep post-recommendation refinements and re-run search "
                    "with the requested filters."
                ),
                issue_key="feedback_filters",
            )
        )
    return flows


def _off_topic_flows() -> list[Flow]:
    first_turn_cases = (
        ("travel", "Can you plan my trip tomorrow?"),
        ("recipe", "Can you give me a dinner recipe?"),
        ("code", "Can you debug my Python code?"),
        ("homework", "Can you help with my homework?"),
    )
    flows = [
        Flow(
            id=f"generated_off_topic_{case_id}",
            summary="Generated off-topic first turn should be redirected.",
            user_inputs=(message,),
            expectations=(
                TurnExpectation(
                    action="redirect",
                    searched=False,
                    not_contains=("I found a few", "Do these feel right"),
                ),
            ),
            project_fix_recommendation=(
                "Detect off-topic questions and briefly redirect back to "
                "watch recommendations."
            ),
            issue_key="off_topic",
        )
        for case_id, message in first_turn_cases
    ]
    flows.append(
        Flow(
            id="generated_off_topic_after_recommendation_recipe",
            summary="Generated off-topic feedback turn should not re-search.",
            user_inputs=(
                "I am bored and want something exciting",
                "Can you give me a dinner recipe?",
            ),
            expectations=(
                TurnExpectation(action="recommend", searched=True),
                TurnExpectation(
                    action="redirect",
                    searched=False,
                    not_contains=("I found a few", "Do these feel right"),
                ),
            ),
            project_fix_recommendation=(
                "When awaiting feedback, classify unrelated questions before "
                "reusing prior recommendation state."
            ),
            issue_key="off_topic",
        )
    )
    return flows


def _copy_flow_with_id(flow: Flow, flow_id: str) -> Flow:
    return Flow(
        id=flow_id,
        summary=flow.summary,
        user_inputs=flow.user_inputs,
        expectations=flow.expectations,
        project_fix_recommendation=flow.project_fix_recommendation,
        issue_key=flow.issue_key,
    )
