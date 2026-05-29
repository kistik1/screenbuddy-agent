# ScreenBuddy

ScreenBuddy is an AI-powered watch recommendation assistant. It helps a user find something to watch by gently understanding their current emotional state, energy, taste, and desired feeling through natural conversation instead of a rigid form.

## Architecture

The Telegram/FastAPI transport is intentionally thin. Conversation behavior lives in the `agent/` package:

- `agent/screenbuddy_agent.py` controls the agent loop.
- `agent/conversation_state.py` stores session memory and structured watch intent.
- `agent/state_extractor.py` maps conversation text into preference state.
- `agent/policy.py` decides whether to ask one follow-up or recommend.
- `agent/search_intent_builder.py` converts state into a search intent.
- `agent/recommendation_ranker.py` ranks and formats personalized recommendations.
- `agent/feedback_handler.py` updates state from post-recommendation feedback.

Existing catalog loading and TF-IDF search remain in `services/`. The agent wraps `services/search_engine.py` instead of replacing the working search integration.

## Conversation Behavior

ScreenBuddy should:

- greet warmly: `Hey, how are you? Want to watch something?`
- ask at most one lightweight follow-up at a time
- infer mood, energy, desired feeling, intensity tolerance, genre hints, runtime hints, and avoidances from casual language
- search once it has a weak emotional signal plus at least one preference, constraint, or inferred direction
- give recommendations with a short personal reason and vibe
- ask `Do these feel right, or should I tune the search?`
- refine from feedback like `not it`, `too heavy`, or `I wanted something more fun` without restarting the session

Telegram commands:

- `/start` clears the current chat session and sends the onboarding message
- `/new` clears the current chat session and starts a fresh recommendation conversation
- `/help` explains how to use the bot without changing the current session

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest
```

Run the FastAPI app:

```bash
uvicorn app:app --reload
```

## Environment

Optional environment variables:

- `OPENAI_API_KEY` enables LLM-based state extraction and recommendation explanation.
- `OPENAI_MODEL` defaults to `gpt-4o-mini`.
- `TELEGRAM_BOT_TOKEN` enables outbound Telegram replies.

Without `OPENAI_API_KEY`, ScreenBuddy uses deterministic heuristic extraction so tests and local development still work.

## Tradeoffs

- Session memory is in process. This is simple and testable, but it will reset on deploy/restart and should move to durable storage for production.
- `/start` and `/new` both clear the same in-memory session keyed by Telegram `chat_id`; there is no durable multi-session history yet.
- The search integration still uses the existing TF-IDF catalog engine. The refactor adds intent building, ranking, and conversational control around it rather than introducing a heavier retrieval stack.
- State extraction keeps the existing legacy analyzer API for compatibility while the new agent package provides the cleaner product architecture.
