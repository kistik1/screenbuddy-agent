# Project Schema

```text
screenbuddy/
|-- .env.example
|-- .gitignore
|-- README.md
|-- SCHEMA.md
|-- app.py
|-- final_master_catalog_with_clusters.csv
|-- requirements.txt
|-- runtime
|-- .idea/
|   |-- .gitignore
|   |-- code.iml
|   |-- misc.xml
|   |-- modules.xml
|   `-- inspectionProfiles/
|       `-- profiles_settings.xml
|-- agent/
|   |-- __init__.py
|   |-- conversation_state.py
|   |-- dialogue_generator.py
|   |-- feedback_handler.py
|   |-- policy.py
|   |-- recommendation_ranker.py
|   |-- screenbuddy_agent.py
|   |-- search_intent_builder.py
|   |-- state_extractor.py
|   `-- topic_router.py
|-- prompts/
|   |-- analyze_feedback_follow_up.txt
|   |-- analyze_user_state.txt
|   |-- classify_topic.txt
|   `-- generate_dialogue.txt
|-- services/
|   |-- catalog_loader.py
|   |-- llm_service.py
|   |-- search_engine.py
|   |-- session_intent_analyzer.py
|   |-- telegram_service.py
|   `-- user_state_analyzer.py
`-- tests/
    |-- test_app_flow.py
    |-- test_session_intent_analyzer.py
    |-- test_tester.py
    |-- test_topic_router.py
    `-- test_user_state_analyzer.py
```

## Main Workflow

```text
[Telegram User]
      |
      v
[POST /webhook]
      |
      +--> [Commands: /start, /new, /help]
      |          |
      |          v
      |    [generate_dialogue()]
      |          |
      |          v
      |    [send_telegram_message()]
      |
      v
[ScreenBuddyAgent.handle_message()]
      |
      +--> [Topic router]
      |          |
      |          +--> [Out of scope reply]
      |
      +--> [Greeting-only check]
      |          |
      |          +--> [Greeting reply]
      |
      +--> [Awaiting feedback]
      |          |
      |          +--> [Session intent analyzer]
      |          |
      |          +--> [Feedback handler]
      |          |
      |          +--> [Refined recommendation]
      |
      v
[User state extraction]
      |
      v
[Conversation session merge]
      |
      v
[Recommendation policy]
      |
      +--> [Needs more signal]
      |          |
      |          v
      |    [Follow-up dialogue]
      |
      v
[Build search intent]
      |
      v
[Search catalog]
      |
      v
[Rank recommendations]
      |
      v
[Recommendation dialogue]
      |
      v
[send_telegram_message()]
```
