# ScreenBuddy Issues Report

- Branch: `v5`
- Requested count: 50000
- Total flows: 50000
- Batch seed: 643154235
- Generation mode: generated
- Passed: 43729
- Failed: 6271


## Top Issues To Change Or Fix

### 1. `filters`

Score: 6269 failed flow(s)

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
- `generated_happy_short_apple_tv_show_adults_action_classic`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm in a good mood and want a light short classic action TV show for adults on Apple TV+.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('happy', 'funny'), got "happy exciting fun high low User message 1: I'm in a good mood and want a light short classic action TV show for adults on Apple TV+. action not horror"
- `generated_stressed_medium_hbo_movie_family_comedy_modern`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm stressed and want a light normal length modern comedy movie for family on Max.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('stressed', 'escape'), got "stressed funny and uplifting low low User message 1: I'm stressed and want a light normal length modern comedy movie for family on Max. comedy not horror"
- `generated_happy_medium_amazon_prime_movie_family_action_modern`: Generated first-turn preference request preserves mood, genre, platform, type, audience, length, and age filters.
  User: I'm in a good mood and want a light normal length modern action movie for family on Prime Video.
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.query_text expected to contain ('happy', 'funny'), got "happy exciting fun high low User message 1: I'm in a good mood and want a light normal length modern action movie for family on Prime Video. action not horror"
- 6265 additional failed flow(s) omitted; use the details report for full transcripts.

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
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
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
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: expected searched == True, got False; intent.intensity_tolerance expected 'low', got None

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

