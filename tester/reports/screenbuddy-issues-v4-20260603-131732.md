# ScreenBuddy Issues Report

- Branch: `v4`
- Requested count: 10000
- Total flows: 10000
- Batch seed: 644858541
- Generation mode: generated
- Passed: 25
- Failed: 9975


## Top Issues To Change Or Fix

### 1. `filters`

Score: 9971 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `filters`.

Recommended change:
- Support audience filters during initial discovery, not only post-recommendation feedback.

Evidence:
- `regular_kids`: Kids/family viewing request gets a family-safe filter.
  User: We need something light for kids after dinner
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: expected searched == True, got False; search.target_audience expected 'kids', got None
- `regular_family`: Family viewing request keeps family audience.
  User: Find a warm family movie for tonight
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=Do you want something easygoing, or are you up for something more absorbing?
  Failed: expected searched == True, got False; search.target_audience expected 'family', got None; search.type expected 'Movie', got None
- `regular_adults`: Adults-only preference reaches search filters.
  User: I want something thoughtful for adults
  Turn 1: expected recommend; searched=True
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: expected searched == True, got False; search.target_audience expected 'adults', got None
- `regular_tv_only`: TV-only initial request uses TV Show filter.
  User: I'm bored, only TV shows please
  Turn 1: expected recommend; searched=True
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: search.type expected 'TV Show', got None
- 9967 additional failed flow(s) omitted; use the details report for full transcripts.

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

### 2. `feedback`

Score: 2 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `feedback`.

Recommended change:
- Expand negative-feedback detection to include bad recommendation language.

Evidence:
- `bad_recommendation_plain`: Bad recommendation feedback should ask for refinement.
  User: I want something relaxing and funny | That is a bad recommendation
  Turn 2: expected ask_refinement; searched=False
  Observed: searched=True; agent=I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - C...
  Failed: expected searched == False, got True; response missing 'wrong vibe'
- `bad_recommendation_wrong_vibe`: Wrong-vibe feedback should ask a refinement question.
  User: I am bored and want something exciting | Wrong vibe, not what I wanted
  Turn 2: expected ask_refinement; searched=False
  Observed: searched=False; agent=Got it. What felt off about them?
  Failed: response missing 'too heavy'; response missing 'too boring'; response missing 'wrong vibe'

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
  Observed: searched=False; agent=What do you want the watch to do for you tonight?
  Failed: response missing 'How was your day'

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

