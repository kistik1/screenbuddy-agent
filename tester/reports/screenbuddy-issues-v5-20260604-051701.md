# ScreenBuddy Issues Report

- Branch: `v5`
- Requested count: 10000
- Total flows: 10000
- Batch seed: 590900797
- Generation mode: generated
- Passed: 8746
- Failed: 1254


## Top Issues To Change Or Fix

### 1. `filters`

Score: 1252 failed flow(s)

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
- `generated_stressed_long_apple_movie_teens_action_modern`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm stressed and want a light long modern action movie for teens on Apple TV+.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('stressed', 'escape'), got "stressed exciting fun low low User message 1: I'm stressed and want a light long modern action movie for teens on Apple TV+. action not horror"
- `generated_stressed_long_netflix_movie_family_action_classic`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm stressed and want a light long classic action movie for family on Netflix.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('stressed', 'escape'), got "stressed exciting fun low low User message 1: I'm stressed and want a light long classic action movie for family on Netflix. action not horror"
- `generated_happy_medium_hulu_movie_family_action_modern`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm in a good mood and want a light normal length modern action movie for family on Hulu.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('happy', 'funny'), got "happy exciting fun high low User message 1: I'm in a good mood and want a light normal length modern action movie for family on Hulu. action not horror"
- 1248 additional failed flow(s) omitted; use the details report for full transcripts.

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

### 2. `discovery`

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

### 3. `avoidances`

Score: 1 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `avoidances`.

Recommended change:
- Convert heavy-content avoidance into low intensity tolerance.

Evidence:
- `regular_avoid_heavy`: Avoid-heavy request keeps low intensity.
  User: I feel fragile, not something heavy
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=What should it do for you tonight: help you switch off, feel cozy, laugh, or get pulled into something exciting?
  Failed: expected searched == True, got False; intent.intensity_tolerance expected 'low', got None

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

