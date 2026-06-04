# ScreenBuddy Tester

This tester runs scripted user-eye conversation flows against a selected git
branch. It does not change the agent implementation. It only executes flows,
checks the agent response against expectations, and writes Markdown reports
with high-scored recommended project fixes plus a separate full detail report.

## Run

From the project root:

```bash
.venv/bin/python -m tester.run --branch v3
```

If you are already inside the `tester/` directory, either go back to the
project root first:

```bash
cd ..
.venv/bin/python -m tester.run --branch v3
```

Or keep your current directory and add the project root to `PYTHONPATH`:

```bash
PYTHONPATH=.. ../.venv/bin/python -m tester.run --branch v3
```

Run a smaller number of flows:

```bash
.venv/bin/python -m tester.run --branch v3 --count 10
```

Run a larger generated batch:

```bash
.venv/bin/python -m tester.run --branch v3 --count 50
```

Rerun a generated batch from a report:

```bash
.venv/bin/python -m tester.run --branch v3 --count 50 --seed 123456
```

Use a custom report directory:

```bash
.venv/bin/python -m tester.run --branch v3 --count 30 --report-dir tester/reports
```

Change the number of summary issues:

```bash
.venv/bin/python -m tester.run --branch v3 --issue-count 5
```

Run with OpenAI-backed calls disabled:

```bash
.venv/bin/python -m tester.run --branch v3 --client none
```

## Parameters

- `--branch`: required git branch to test.
- `--count`: exact number of generated flows to run. Default is `30`.
- `--report-dir`: optional output directory. Default is `tester/reports`.
- `--seed`: optional generated batch seed. Omit it for a new random batch each
  run; pass a seed from a report to rerun the same batch.
- `--issue-count`: optional number of high-scored summary issues. Default is
  `3`.
- `--client`: optional LLM client mode, either `live` or `none`. Default is
  `live`; use `none` to disable OpenAI-backed calls and use fallback behavior.

## Output

The tester prints progress for each flow and writes two reports like:

```text
tester/reports/screenbuddy-issues-v3-20260603-120000.md
tester/reports/screenbuddy-details-v3-20260603-120000.md
```

Relative report paths are resolved from the project root.

The issues report includes:

- requested count, actual flow count, generated batch seed, and generation mode,
- final summary with the requested number of high-scored issues to fix,
- a compact Codex prompt for each issue with the recommended change, capped
  failure evidence, and success criteria.

The details report includes:

- requested count, actual flow count, generated batch seed, and generation mode,
- each test summary,
- user inputs,
- agent responses,
- expected behavior,
- pass/fail checks,
- a recommendation for what to change in the project.

## Exit Code

- `0`: all selected flows passed.
- `1`: one or more flows failed.

A failing exit code is expected when the tester finds user-facing issues. Read
the generated issues report to decide what to fix, and use the details report
to inspect every test.

## Branch Safety

The tester checks for tracked working-tree changes only before switching
branches. If you run against the current branch, local tracked edits are tested
as-is. If the requested branch is different and tracked files are dirty, it
stops and asks you to commit or stash first. Untracked files are ignored by this
safety check.

## Common Problems

If `python` does not work, use the project virtual environment explicitly:

```bash
.venv/bin/python -m tester.run --branch v3
```

If you run the command from inside `tester/`, use one of these:

```bash
cd ..
.venv/bin/python -m tester.run --branch v3
```

```bash
PYTHONPATH=.. ../.venv/bin/python -m tester.run --branch v3
```

If the command exits with `1`, that usually means the tester found failed
flows. Open the generated issues Markdown report and read the Codex prompts.
