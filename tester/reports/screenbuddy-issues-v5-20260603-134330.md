# ScreenBuddy Issues Report

- Branch: `v5`
- Requested count: 10000
- Total flows: 10000
- Batch seed: 1958602655
- Generation mode: generated
- Passed: 8717
- Failed: 1283


## Top Issues To Change Or Fix

### 1. `filters`

Score: 1281 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `filters`.

Recommended change:
- Extract classic/older age preferences during initial discovery.

Evidence:
- `regular_classic`: Classic preference reaches age category.
  User: I want a classic cozy movie
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: expected searched == True, got False; search.age_category expected 'classic', got None; search.type expected 'Movie', got None
- `regular_romance`: Romance genre is preserved.
  User: I want a sweet romance that is easy to watch
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: expected searched == True, got False; intent.genres expected to include ('romance',), got None
- `regular_documentary`: Documentary request preserves genre.
  User: I want a thoughtful documentary tonight
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: expected searched == True, got False; intent.genres expected to include ('documentary',), got None
- `regular_language`: Language preference should be retained.
  User: I want something relaxing in Spanish
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: intent.language_preference expected 'spanish', got None
- 1277 additional failed flow(s) omitted; use the details report for full transcripts.

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

