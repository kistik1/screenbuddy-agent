# ScreenBuddy Issues Report

- Branch: `v5`
- Requested count: 5
- Total flows: 5
- Batch seed: 47825888
- Generation mode: generated
- Passed: 4
- Failed: 1


## Top Issues To Change Or Fix

### 1. `filters`

Score: 1 failed flow(s)

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

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

### 2. `feedback`

Score: 0 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `feedback`.

Recommended change:
- Add positive-feedback handling so acceptance does not trigger a new search or another tuning prompt.

Evidence:
- No failed flow was captured in this run.
- Representative flow: `approval_accepts_final`: User approval should close the recommendation loop.
- User: I had a long day and want something light and funny | Yes, these feel right

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

### 3. `intent_extraction`

Score: 0 failed flow(s)

Exact Codex prompt:

```text
Fix ScreenBuddy tester issue `intent_extraction`.

Recommended change:
- Improve state extraction for tired/light/funny language and ensure the search intent carries those signals.

Evidence:
- No failed flow was captured in this run.
- Representative flow: `regular_tired_light`: Tired and light request produces easy recommendations.
- User: I had a long day and want something light and funny

Success criteria:
- Make the smallest project change that satisfies this issue.
- Add or update focused tests for the behavior you change.
- Run the relevant tests and report the command result.
```

