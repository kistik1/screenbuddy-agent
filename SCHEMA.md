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
|-- tester/
|   |-- README.md
|   |-- __init__.py
|   |-- evaluator.py
|   |-- flows.py
|   |-- report.py
|   |-- run.py
|   `-- reports/
|       |-- screenbuddy-details-v4-20260603-131732.md
|       |-- screenbuddy-details-v5-20260603-134304.md
|       |-- screenbuddy-details-v5-20260603-134330.md
|       |-- screenbuddy-details-v5-20260603-140450.md
|       |-- screenbuddy-details-v5-20260603-143316.md
|       |-- screenbuddy-details-v5-20260604-051701.md
|       |-- screenbuddy-details-v5-20260604-055837.md
|       |-- screenbuddy-details-v5-20260604-062430.md
|       |-- screenbuddy-issues-v4-20260603-131732.md
|       |-- screenbuddy-issues-v5-20260603-134304.md
|       |-- screenbuddy-issues-v5-20260603-134330.md
|       |-- screenbuddy-issues-v5-20260603-140450.md
|       |-- screenbuddy-issues-v5-20260603-143316.md
|       |-- screenbuddy-issues-v5-20260604-051701.md
|       |-- screenbuddy-issues-v5-20260604-055837.md
|       `-- screenbuddy-issues-v5-20260604-062430.md
`-- tests/
    |-- test_app_flow.py
    |-- test_session_intent_analyzer.py
    |-- test_tester.py
    |-- test_topic_router.py
    `-- test_user_state_analyzer.py
```
