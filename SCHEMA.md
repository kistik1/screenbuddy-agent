# SCHEMA

## Project Shape

```text
code/
|-- app.py
|   -> FastAPI entrypoint, health endpoints, Telegram webhook, agent wiring
|-- final_master_catalog_with_clusters.csv
|   -> catalog source loaded at startup
|-- agent/
|   |-- conversation_state.py
|   |   -> session store, user preference state, search intent dataclasses
|   |-- dialogue_generator.py
|   |   -> LLM-first user-facing dialogue generation with centralized fallback copy
|   |-- feedback_handler.py
|   |   -> post-recommendation feedback detection and deterministic state/filter refinement
|   |-- policy.py
|   |   -> deterministic recommendation-readiness and follow-up target policy
|   |-- recommendation_ranker.py
|   |   -> intent-aware reranking
|   |-- screenbuddy_agent.py
|   |   -> top-level conversation orchestrator
|   |-- search_intent_builder.py
|   |   -> maps session state into search intent
|   `-- state_extractor.py
|       -> maps analyzer output into agent-facing preference state
|-- prompts/
|   |-- analyze_user_state.txt
|   |   -> system prompt for structured user-state extraction
|   `-- generate_dialogue.txt
|       -> system prompt for generated ScreenBuddy dialogue
|-- services/
|   |-- catalog_loader.py
|   |   -> catalog validation, derived fields, TF-IDF index build
|   |-- llm_service.py
|   |   -> OpenAI client setup and prompt loading helpers
|   |-- search_engine.py
|   |   -> metadata filters and semantic search over the catalog
|   |-- telegram_service.py
|   |   -> Telegram send-message integration
|   `-- user_state_analyzer.py
|       -> structured extraction backend used by the agent state extractor
`-- tests/
    |-- test_app_flow.py
    |   -> agent conversation and webhook coverage
    `-- test_user_state_analyzer.py
        -> analyzer normalization and fallback coverage
```

## Runtime Flow

```text
[Telegram User]
      |
      v
[POST /webhook]
  Read message, chat_id, text
      |
      +--> /start, /new, /help
      |    Reset/preserve session as needed
      |    Generate command dialogue by phase
      |    Send message
      |
      v
[ScreenBuddyAgent.handle_message()]
  Load or create ConversationSession
  Append latest message
      |
      +--> first message is greeting-only
      |    Store state and generate greeting dialogue
      |
      +--> awaiting_feedback
      |    Apply deterministic feedback refinements
      |    If changed -> recommend again
      |    If vague negative -> generate one clarification question
      |
      v
[extract_state()]
  analyze_user_state(conversation_text)
  Map analyzer output into UserPreferenceState
  Merge signal into session state
      |
      v
[policy.should_recommend()]
  Deterministically decide whether enough signal exists
      |
      +--> false
      |    Store session
      |    Generate one discovery follow-up from structured target
      |
      v
[ScreenBuddyAgent._recommend()]
  build_watch_search_intent(session.user_state, filters)
  intent.to_search_query()
  search_titles(...)
  rank_recommendations(...)
  Generate recommendation or no-results dialogue
  Store last intent/recommendations and feedback state
      |
      v
[send_telegram_message()]
  Deliver generated message to Telegram user
```

## Deterministic Responsibilities

- Conversation state and phase transitions.
- Deciding when enough user signal exists to search.
- Building search intent and calling the existing search engine.
- Catalog filtering, TF-IDF search, and intent-aware reranking.
- Parsing actionable recommendation feedback into state/filter updates.
- Triggering re-search when feedback changes the state or filters.

## LLM Dialogue Responsibilities

- Greeting, onboarding, help, and session reset copy.
- Discovery follow-up wording from a deterministic follow-up target.
- Recommendation messages grounded in the provided recommendation payload.
- No-results and vague-feedback clarification questions.

The dialogue generator must ask at most one question, avoid form-like mood collection, avoid invented catalog facts, and always ask whether recommendation results feel right.

## Core Data Contracts

`ScreenBuddyAgent.handle_message()` returns:

```text
message: str
searched: bool
intent: WatchSearchIntent | None
```

`UserPreferenceState` stores:

```text
current_mood: str
desired_feeling: str
energy_level: low | medium | high | unknown
intensity_tolerance: low | medium | high | unknown
genres: list[str]
avoid_genres: list[str]
runtime_preference: str
language_preference: str
platform_preference: str
free_text_context: str
confidence: float
```

`services.user_state_analyzer.analyze_user_state()` returns structured extraction only:

```text
user_state:
  mood: happy | sad | stressed | tired | bored | neutral | unknown
  energy_level: low | medium | high | unknown
  viewing_intent: relax | escape | laugh | get_excited | feel_comforted | think_deeply | unknown
  content_complexity: low | medium | high | unknown
  preferred_length: short | medium | long | unknown
  avoid: list[str]
  confidence: float in [0.0, 1.0]
  missing_info: list[str]
needs_follow_up: bool
```

`WatchSearchIntent.to_search_query()` returns:

```text
query_text: str
release_year_min: int | None
release_year_max: int | None
duration_preference: short | medium | long | None
target_audience: str | None
age_category: str | None
streaming: str | None
type: str | None
```

`services.search_engine.search_titles()` returns recommendation dictionaries with title, genres, description, type, release year, duration, audience, age category, streaming, similarity score, cluster metadata, and related titles.

## Runtime Constants

- `TOP_N = 3`
- `MIN_SIMILARITY = 0.2`
- `MAX_AGENT_FOLLOW_UPS = 3`
- `ConversationSessionStore` is in-memory and keyed by Telegram `chat_id`.
- `OPENAI_API_KEY` enables LLM extraction and dialogue; without it, heuristic extraction and centralized fallback dialogue keep local tests working.
