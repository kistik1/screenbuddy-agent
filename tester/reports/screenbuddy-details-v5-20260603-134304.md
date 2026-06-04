# ScreenBuddy Test Details Report

- Branch: `v5`
- Requested count: 5
- Total flows: 5
- Batch seed: 47825888
- Generation mode: generated
- Passed: 4
- Failed: 1

## Flow Results

### PASS: approval_pick_one

Summary: User choosing a recommendation should be acknowledged.

Transcript:
- Turn 1 user: I'm sad and want something comforting
- Turn 1 agent: I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - Comedy, Family | 2024 | 90 min Do these feel right, or should I tune the search?
- Turn 1 expected: recommend; searched=True
- Turn 1 search: {'query_text': "sad comfort low User message 1: I'm sad and want something comforting", 'release_year_min': None, 'release_year_max': None, 'duration_preference': None, 'target_audience': None, 'age_category': None, 'streaming': None, 'type': None}
- Turn 2 user: The first one sounds good
- Turn 2 agent: Good watching time.
- Turn 2 expected: accept; searched=False

Recommended project fix: Treat explicit selection of a recommended title as acceptance.

### PASS: regular_bored_exciting

Summary: Bored user asking for excitement gets an energetic direction.

Transcript:
- Turn 1 user: I'm bored and want something exciting tonight
- Turn 1 agent: I found a few that could fit: <b>Easy Match</b> - Comedy, Family | 2024 | 90 min <b>Second Option</b> - Comedy, Family | 2024 | 90 min <b>Third Pick</b> - Comedy, Family | 2024 | 90 min Do these feel right, or should I tune the search?
- Turn 1 expected: recommend; searched=True
- Turn 1 search: {'query_text': "bored exciting fun medium User message 1: I'm bored and want something exciting tonight", 'release_year_min': None, 'release_year_max': None, 'duration_preference': None, 'target_audience': None, 'age_category': None, 'streaming': None, 'type': None}

Recommended project fix: Map boredom and excitement into a stronger search query and ranking reason.

### PASS: irrelevant_smalltalk_first

Summary: Small talk should be handled without searching.

Transcript:
- Turn 1 user: Do you like pizza?
- Turn 1 agent: What do you want the watch to do for you tonight?
- Turn 1 expected: redirect; searched=False

Recommended project fix: Handle casual off-topic small talk with a short redirect.

### FAIL: regular_classic

Summary: Classic preference reaches age category.

Failures:
- turn 1: expected searched == True, got False
- turn 1: search.age_category expected 'classic', got None
- turn 1: search.type expected 'Movie', got None

Transcript:
- Turn 1 user: I want a classic cozy movie
- Turn 1 agent: What do you want the watch to do for you tonight?
- Turn 1 expected: recommend; searched=True

Recommended project fix: Extract classic/older age preferences during initial discovery.

### PASS: regular_greeting

Summary: Greeting starts a warm watch conversation.

Transcript:
- Turn 1 user: Hello
- Turn 1 agent: Hey, how are you? Want to watch something?
- Turn 1 expected: ask_follow_up; searched=False

Recommended project fix: Keep greetings focused on inviting the user into a watch choice instead of searching immediately.
