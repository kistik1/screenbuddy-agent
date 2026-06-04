# ScreenBuddy Issues Report

- Branch: `v5`
- Requested count: 50000
- Total flows: 50000
- Batch seed: 1091292743
- Generation mode: generated
- Passed: 43701
- Failed: 6299


## Top Issues To Change Or Fix

### 1. `filters`

Score: 6267 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `filters`.

Recommended change:
- Add language extraction so language preferences affect search.

Evidence:
- `regular_language`: Language preference should be retained.
  User: I want something relaxing in Spanish
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: intent.language_preference expected 'spanish', got None
- `generated_stressed_medium_hulu_tv_show_teens_thriller_recent`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm stressed and want a light normal length recent thriller TV show for teens on Hulu.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('stressed', 'escape'), got "stressed exciting fun low low User message 1: I'm stressed and want a light normal length recent thriller TV show for teens on Hulu. thriller not horror"
- `generated_stressed_medium_disney_movie_family_thriller_recent`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm stressed and want a light normal length recent thriller movie for family on Disney+.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('stressed', 'escape'), got "stressed exciting fun low low User message 1: I'm stressed and want a light normal length recent thriller movie for family on Disney+. thriller not horror"
- `generated_happy_long_hulu_tv_show_adults_action_recent`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm in a good mood and want a light long recent action TV show for adults on Hulu.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('happy', 'funny'), got "happy exciting fun high low User message 1: I'm in a good mood and want a light long recent action TV show for adults on Hulu. action not horror"
- 6263 additional failed flow(s) omitted; use the details report for full transcripts.

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

### 2. `feedback_filters`

Score: 30 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `feedback_filters`.

Recommended change:
- Keep post-recommendation platform refinements and re-run search with the requested streaming filter.

Evidence:
- `change_final_netflix_only`: Final recommendation can be changed to Netflix only.
  User: I had a long day and want something light and funny | Netflix only
  Turn 2: expected recommend; searched=True
  Observed: searched=False; agent=Got it. Sounds like the wrong vibe. Was it too heavy, too boring, or just not the kind of feel you wanted?
  Failed: expected searched == True, got False; search.streaming expected 'netflix', got None
- `generated_feedback_after_2018`: Generated feedback refinement updates search filters.
  User: I had a long day and want something light and funny | after 2018
  Turn 2: expected recommend; searched=True
  Observed: searched=False; agent=Got it. Sounds like the wrong vibe. Was it too heavy, too boring, or just not the kind of feel you wanted?
  Failed: expected searched == True, got False; response missing 'Do these feel right'; search.release_year_min expected 2018, got None
- `generated_feedback_tv_show`: Generated feedback refinement updates search filters.
  User: I had a long day and want something light and funny | only TV shows
  Turn 2: expected recommend; searched=True
  Observed: searched=False; agent=Got it. Sounds like the wrong vibe. Was it too heavy, too boring, or just not the kind of feel you wanted?
  Failed: expected searched == True, got False; response missing 'Do these feel right'; search.type expected 'TV Show', got None
- `generated_feedback_classic`: Generated feedback refinement updates search filters.
  User: I had a long day and want something light and funny | make it classic
  Turn 2: expected recommend; searched=True
  Observed: searched=False; agent=Got it. Sounds like the wrong vibe. Was it too heavy, too boring, or just not the kind of feel you wanted?
  Failed: expected searched == True, got False; response missing 'Do these feel right'; search.age_category expected 'classic', got None
- 26 additional failed flow(s) omitted; use the details report for full transcripts.

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

### 3. `discovery`

Score: 1 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `discovery`.

Recommended change:
- Tune the discovery policy to ask one lightweight emotional question before recommending from vague requests.

Evidence:
- `regular_vague_request`: Vague watch request asks one human follow-up.
  User: Can you help me find something to watch?
  Turn 1: expected ask_follow_up; searched=False
  Observed: searched=False; agent=What should it do for you tonight: help you switch off, feel cozy, laugh, or get pulled into something exciting?
  Failed: response missing 'How was your day'

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

