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
|   |-- feedback_handler.py
|   |   -> post-recommendation feedback detection and state refinement
|   |-- policy.py
|   |   -> follow-up and recommendation decision policy
|   |-- recommendation_ranker.py
|   |   -> intent-aware reranking and final recommendation message formatting
|   |-- screenbuddy_agent.py
|   |   -> top-level conversation orchestrator
|   |-- search_intent_builder.py
|   |   -> maps session state into search intent
|   `-- state_extractor.py
|       -> maps analyzer output into agent-facing preference state
|-- prompts/
|   |-- analyze_user_state.txt
|   |   -> system prompt for user-state extraction
|   |-- generate_recommendation.txt
|   |   -> system prompt for explanation generation
|   `-- parse_user_query.txt
|       -> present in repo, currently unused
|-- services/
|   |-- catalog_loader.py
|   |   -> catalog validation, derived fields, TF-IDF index build
|   |-- llm_service.py
|   |   -> OpenAI client setup, prompt loading, explanation generation
|   |-- search_engine.py
|   |   -> metadata filters and semantic search over the catalog
|   |-- telegram_service.py
|   |   -> Telegram send-message integration
|   `-- user_state_analyzer.py
|       -> legacy analyzer backend used by the agent state extractor
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
      +--> /start
      |    screenbuddy_agent.reset(chat_id)
      |    Send onboarding message
      |    Return {"ok": true}
      |
      +--> /new
      |    screenbuddy_agent.reset(chat_id)
      |    Send fresh-session message
      |    Return {"ok": true}
      |
      +--> /help
      |    Send usage message
      |    Return {"ok": true}
      |
      v
[ScreenBuddyAgent.handle_message()]
  Load or create ConversationSession
  Append latest message
      |
      +--> first message is greeting-only
      |    Increment follow_up_count
      |    Store session
      |    Return warm invitation message
      |
      +--> awaiting_feedback
      |    Try feedback refinement
      |    If feedback changes state -> recommend again
      |    Else if feedback is negative -> ask refinement question
      |
      v
[extract_state()]
  analyze_user_state(conversation_text)
  Map analyzer output into UserPreferenceState
  Merge new signal into session state
      |
      v
[policy.should_recommend()]
  Recommend when:
  - emotional signal + directional signal exist, or
  - confidence >= 0.75 with emotional signal, or
  - follow-up cap has been reached
      |
      +--> false
      |    Increment follow_up_count
      |    Store session
      |    Return next_follow_up(...)
      |
      v
[ScreenBuddyAgent._recommend()]
  build_watch_search_intent(session.user_state)
  intent.to_search_query()
  search_titles(...)
  rank_recommendations(...)
  generate_recommendation_explanation(...)
  format_personal_recommendations(...)
  Set awaiting_feedback = true
  Store session
      |
      v
[send_telegram_message()]
  Deliver final message to Telegram user
```

## Endpoints

- `GET /`
  Returns service status and `records_loaded`.
- `GET /health`
  Returns `"ok"` health status, service name, and `records_loaded`.
- `HEAD /`
  Empty root response.
- `HEAD /health`
  Empty health response.
- `POST /webhook`
  Main Telegram webhook endpoint for onboarding, session reset, usage help, conversational discovery, recommendations, and recommendation feedback.

## Current Runtime State

- `TOP_N = 3`
  The app asks the search layer for up to three titles.
- `MIN_SIMILARITY = 0.2`
  Weak semantic matches below this score are dropped.
- `MAX_AGENT_FOLLOW_UPS = 2`
  The agent asks at most two discovery follow-ups before forcing a recommendation pass.
- `ConversationSessionStore`
  Session state is in memory only and keyed by Telegram `chat_id`.
- OpenAI usage is optional
  Without `OPENAI_API_KEY`, analyzer extraction falls back to heuristics and explanation generation is skipped.

## Data Contracts In Practice

### Telegram Webhook Input

The webhook expects Telegram-style JSON with this practical shape:

```json
{
  "message": {
    "chat": {
      "id": 123
    },
    "text": "I had a long day and want something light"
  }
}
```

If `chat_id` is missing, the app returns:

```json
{
  "ok": false,
  "error": "missing chat_id"
}
```

### Agent Response

`ScreenBuddyAgent.handle_message()` returns:

```text
message: str
searched: bool
intent: WatchSearchIntent | None
```

The webhook sends `message` directly to Telegram and always returns `{ "ok": true }` on successful handling.

Supported command messages:

- `/start`
  Clears the current `chat_id` session and sends onboarding copy.
- `/new`
  Clears the current `chat_id` session and sends fresh-session copy.
- `/help`
  Sends usage guidance and preserves the current session state.

### Conversation Session

`ConversationSessionStore` stores `ConversationSession` objects with:

```text
chat_id: int
messages: list[str]
user_state: UserPreferenceState
follow_up_count: int
last_intent: WatchSearchIntent | None
last_recommendations: list[dict]
awaiting_feedback: bool
updated_at: unix timestamp
```

This store is process-local and survives only for the current Python process.
Both `/start` and `/new` clear this store entry for the current `chat_id`.

### User Preference State

The agent works with `UserPreferenceState`:

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

Behavioral notes:

- `merge()` preserves existing state and only overwrites scalar fields with non-`unknown` incoming values.
- `genres` and `avoid_genres` are accumulated uniquely across turns.
- `has_emotional_signal()` means `current_mood` or `desired_feeling` is known.
- `has_directional_signal()` means at least one of energy, intensity, runtime, language, platform, genres, or avoid-genres is known.

### Analyzer Output

`services/user_state_analyzer.py` still provides the extraction backend used by `agent/state_extractor.py`.

Its normalized result shape is:

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
assistant_reply: str
follow_up_questions: list[str]
```

`agent/state_extractor.py` maps this legacy analyzer shape into:

- `mood -> current_mood`
- `viewing_intent -> desired_feeling`
  - `relax -> easy comfort`
  - `escape -> distraction and escape`
  - `laugh -> funny and uplifting`
  - `get_excited -> exciting fun`
  - `feel_comforted -> comfort`
  - `think_deeply -> thoughtful`
- `content_complexity` and avoid-list cues into `intensity_tolerance`
- `preferred_length -> runtime_preference`
- `avoid -> avoid_genres`

### Watch Search Intent

`build_watch_search_intent()` produces `WatchSearchIntent`:

```text
desired_feeling: str | None
current_mood: str | None
energy_level: str | None
intensity_tolerance: str | None
genres: list[str]
avoid_genres: list[str]
runtime_preference: short | medium | long | None
language_preference: str | None
platform_preference: str | None
free_text_context: str
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

Current mapping details:

- `query_text` is built from mood, desired feeling, energy, intensity, free-text context, genres, and `not <genre>` exclusions.
- `duration_preference` comes from `runtime_preference`.
- `streaming` comes from `platform_preference`.
- other search filters currently default to `None`.

### Recommendation Object

`services/search_engine.search_titles()` returns recommendation objects with:

```text
title: str
genres: str
description: str
type: str
release_year: str
duration: str
target_audience: str
age_category: str
streaming: str
similarity_score: float
cluster_id: str
cluster_name: str
dbscan_cluster: str
is_outlier: bool
more_from_cluster: list[str]
```

The agent then:

- re-ranks these objects with `rank_recommendations(...)`
- optionally adds an LLM explanation
- formats the final user-visible message with `format_personal_recommendations(...)`

Current final response behavior:

- If no strong matches remain, the user gets:
  `I couldn't find a strong match yet. Want to steer me toward something lighter, funnier, cozier, or more exciting?`
- If results exist, the user gets up to three personalized title cards followed by:
  `Do these feel right, or should I tune the search?`

### Feedback Handling

After a recommendation pass:

- `awaiting_feedback` is set to `true`
- negative feedback is detected with phrases such as:
  `no`, `not it`, `not quite`, `try again`, `wrong vibe`
- state can be refined from feedback like:
  - `more fun`, `funnier`, `playful`
  - `lighter`, `too heavy`
  - `too boring`, `more exciting`
  - `cozier`, `more cozy`

If negative feedback is detected without actionable refinement, the agent asks:

`Got it — was it too heavy, too boring, or just the wrong vibe?`

## Catalog Data

### Required Source Columns

`catalog_loader.py` ensures these columns exist before indexing:

```text
title
description
genre_1
genre_2
genre_3
cluster_kmeans
cluster_name
cluster_dbscan
is_outlier
release_year
duration
target_audience
age_category
streaming
type
```

### Derived Fields

The loader creates:

- `listed_in`
  Combined genre string from `genre_1`, `genre_2`, and `genre_3`.
- `combined_text`
  Lowercased text field used for TF-IDF search across:
  `title`, `description`, `listed_in`, `cluster_name`, `release_year`, `duration`, `target_audience`, `age_category`, `streaming`, and `type`.

### Normalization And Indexing

- `release_year` is converted to numeric with invalid values coerced to null.
- TF-IDF uses custom stop words on top of scikit-learn English stop words.
- The vectorizer is capped at `max_features=5000`.

## Search And Ranking Notes

- Filtering happens before semantic ranking.
- Supported search-engine filters are:
  `release_year_min`, `release_year_max`, `streaming`, `target_audience`, `age_category`, `type`, and `duration_preference`.
- `duration_preference` is implemented with string-pattern matching on `duration`.
- Similarity is computed with cosine similarity over the filtered TF-IDF matrix.
- Additional titles are sampled from the same `cluster_kmeans` group.
- Agent-side reranking adds intent-sensitive boosts and penalties, especially for low-intensity, comfort, and funny/uplifting requests.

## Status Notes

- The app now has one top-level conversation controller: `ScreenBuddyAgent`.
- `services/user_state_analyzer.py` remains active, but as a lower-level extraction dependency rather than the webhook orchestrator.
- Greeting-only first turns, discovery follow-ups, recommendation output, and recommendation feedback are all part of the current supported runtime flow.
- `services/search_engine.format_recommendations_message()` still exists, but it is no longer the primary final formatter used by the webhook path.
- `parse_user_query.txt` exists in the repo but is not part of the current runtime flow.
