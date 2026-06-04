from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tester.evaluator import FlowResult
from tester.flows import FLOWS, Flow


MAX_PROMPT_EXAMPLES = 4
MAX_PROMPT_FAILURES_PER_EXAMPLE = 3
PROMPT_TEXT_LIMIT = 180


@dataclass(frozen=True)
class ReportPaths:
    issues: Path
    details: Path


def write_report(
    *,
    branch: str,
    results: list[FlowResult],
    report_dir: Path,
    issue_count: int = 3,
    requested_count: int | None = None,
    batch_seed: int | None = None,
    generation_mode: str | None = None,
) -> ReportPaths:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    paths = ReportPaths(
        issues=report_dir / f"screenbuddy-issues-{branch}-{stamp}.md",
        details=report_dir / f"screenbuddy-details-{branch}-{stamp}.md",
    )
    paths.issues.write_text(
        render_issues_report(
            branch=branch,
            results=results,
            issue_count=issue_count,
            requested_count=requested_count,
            batch_seed=batch_seed,
            generation_mode=generation_mode,
        ),
        encoding="utf-8",
    )
    paths.details.write_text(
        render_details_report(
            branch=branch,
            results=results,
            requested_count=requested_count,
            batch_seed=batch_seed,
            generation_mode=generation_mode,
        ),
        encoding="utf-8",
    )
    return paths


def render_issues_report(
    *,
    branch: str,
    results: list[FlowResult],
    issue_count: int = 3,
    requested_count: int | None = None,
    batch_seed: int | None = None,
    generation_mode: str | None = None,
) -> str:
    lines = [
        "# ScreenBuddy Issues Report",
        "",
        *_render_metadata(
            branch=branch,
            results=results,
            requested_count=requested_count,
            batch_seed=batch_seed,
            generation_mode=generation_mode,
        ),
        "",
    ]
    lines.extend(_render_top_issues(results, issue_count=issue_count))
    return "\n".join(lines) + "\n"


def render_details_report(
    *,
    branch: str,
    results: list[FlowResult],
    requested_count: int | None = None,
    batch_seed: int | None = None,
    generation_mode: str | None = None,
) -> str:
    lines = [
        "# ScreenBuddy Test Details Report",
        "",
        *_render_metadata(
            branch=branch,
            results=results,
            requested_count=requested_count,
            batch_seed=batch_seed,
            generation_mode=generation_mode,
        ),
        "",
        "## Flow Results",
    ]
    for result in results:
        lines.extend(_render_flow(result))
    return "\n".join(lines) + "\n"


def render_report(
    *,
    branch: str,
    results: list[FlowResult],
    issue_count: int = 3,
    requested_count: int | None = None,
    batch_seed: int | None = None,
    generation_mode: str | None = None,
) -> str:
    lines = [
        "# ScreenBuddy User-Eyes Tester Report",
        "",
        *_render_metadata(
            branch=branch,
            results=results,
            requested_count=requested_count,
            batch_seed=batch_seed,
            generation_mode=generation_mode,
        ),
        "",
        "## Flow Results",
    ]
    for result in results:
        lines.extend(_render_flow(result))
    lines.extend(_render_top_issues(results, issue_count=issue_count))
    return "\n".join(lines) + "\n"


def _render_metadata(
    *,
    branch: str,
    results: list[FlowResult],
    requested_count: int | None,
    batch_seed: int | None,
    generation_mode: str | None,
) -> list[str]:
    total = len(results)
    passed = sum(1 for result in results if result.status == "PASS")
    failed = total - passed
    return [
        f"- Branch: `{branch}`",
        f"- Requested count: {requested_count if requested_count is not None else total}",
        f"- Total flows: {total}",
        f"- Batch seed: {batch_seed if batch_seed is not None else 'not recorded'}",
        f"- Generation mode: {generation_mode or 'static'}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
    ]


def _render_flow(result: FlowResult) -> list[str]:
    flow = result.flow
    lines = [
        "",
        f"### {result.status}: {flow.id}",
        "",
        f"Summary: {flow.summary}",
        "",
    ]
    if result.failed_checks:
        lines.append("Failures:")
        lines.extend(f"- {failure}" for failure in result.failed_checks)
        lines.append("")

    lines.append("Transcript:")
    for index, turn in enumerate(result.turns, start=1):
        lines.append(f"- Turn {index} user: {turn.user_input}")
        lines.append(f"- Turn {index} agent: {_one_line(turn.agent_response)}")
        lines.append(
            f"- Turn {index} expected: {turn.expectation.action}; "
            f"searched={turn.expectation.searched}"
        )
        if turn.search_call:
            lines.append(
                f"- Turn {index} search: {turn.search_call.get('parsed_query')}"
            )
    lines.extend(
        [
            "",
            f"Recommended project fix: {flow.project_fix_recommendation}",
        ]
    )
    return lines


def _render_top_issues(
    results: list[FlowResult],
    *,
    issue_count: int,
) -> list[str]:
    if issue_count < 1:
        raise ValueError("issue_count must be at least 1")

    selected = _select_top_issues(results, issue_count=issue_count)
    lines = ["", "## Top Issues To Change Or Fix", ""]
    for index, (issue_key, issue_results) in enumerate(selected, start=1):
        sample = issue_results[0].flow if issue_results else _sample_flow(issue_key)
        score = len([result for result in issue_results if result.status == "FAIL"])
        lines.extend(
            [
                f"### {index}. `{issue_key}`",
                "",
                f"Score: {score} failed flow(s)",
                "",
                "Exact Codex prompt:",
                "",
                "```text",
                _codex_prompt(issue_key, issue_results, sample),
                "```",
                "",
            ]
        )
    return lines


def _select_top_issues(
    results: list[FlowResult],
    *,
    issue_count: int,
) -> list[tuple[str, list[FlowResult]]]:
    failed = [result for result in results if result.status == "FAIL"]
    grouped: dict[str, list[FlowResult]] = defaultdict(list)
    for result in failed:
        grouped[result.flow.issue_key].append(result)

    flow_order = _flow_order()
    selected: list[tuple[str, list[FlowResult]]] = [
        (key, grouped[key])
        for key in sorted(
            grouped,
            key=lambda issue_key: (
                -len(grouped[issue_key]),
                flow_order.get(issue_key, len(FLOWS)),
            ),
        )
    ]

    if len(selected) < issue_count:
        for result in results:
            candidate = (result.flow.issue_key, [])
            if any(existing[0] == candidate[0] for existing in selected):
                continue
            selected.append(candidate)
            if len(selected) == issue_count:
                break

    if len(selected) < issue_count:
        for flow in FLOWS:
            if any(existing[0] == flow.issue_key for existing in selected):
                continue
            selected.append((flow.issue_key, []))
            if len(selected) == issue_count:
                break

    return selected[:issue_count]


def _render_issue_situations(
    issue_results: list[FlowResult],
    sample: Flow,
) -> list[str]:
    if not issue_results:
        return [
            "- No failed flow in this run. Use this as a fallback issue to inspect.",
            f"  Representative flow: `{sample.id}` - {sample.summary}",
        ]

    lines: list[str] = []
    for result in issue_results:
        lines.append(f"- `{result.flow.id}`: {result.flow.summary}")
        for index, turn in enumerate(result.turns, start=1):
            lines.append(f"  Turn {index} user: {turn.user_input}")
            lines.append(f"  Turn {index} expected: {_expected_summary(turn)}")
            lines.append(f"  Turn {index} observed: {_observed_summary(turn)}")
        if result.failed_checks:
            lines.append(f"  Failed checks: {'; '.join(result.failed_checks)}")
    return lines


def _codex_prompt(
    issue_key: str,
    issue_results: list[FlowResult],
    sample: Flow,
) -> str:
    lines = [
        f"Fix ScreenBuddy tester issue `{issue_key}`.",
        "",
        "Recommended change:",
        f"- {sample.project_fix_recommendation}",
        "",
        "Evidence:",
    ]
    if not issue_results:
        lines.extend(
            [
                "- No failed flow was captured in this run.",
                f"- Representative flow: `{sample.id}`: {sample.summary}",
                f"- User: {_compact_text(' | '.join(sample.user_inputs))}",
            ]
        )
    else:
        prompt_results = issue_results[:MAX_PROMPT_EXAMPLES]
        for result in prompt_results:
            lines.extend(_render_prompt_example(result))

        omitted = len(issue_results) - len(prompt_results)
        if omitted > 0:
            lines.append(
                f"- {omitted} additional failed flow(s) omitted; use the details "
                "report for full transcripts."
            )

    lines.extend(
        [
            "",
            "Success criteria:",
            "- Make the smallest project change that satisfies this issue.",
            "- Add or update focused tests for the behavior you change.",
            "- Run the relevant tests and report the command result.",
        ]
    )
    return "\n".join(lines)


def _render_prompt_example(result: FlowResult) -> list[str]:
    lines = [
        f"- `{result.flow.id}`: {result.flow.summary}",
        f"  User: {_compact_text(' | '.join(result.flow.user_inputs))}",
    ]
    for index, turn in enumerate(result.turns, start=1):
        if turn.passed:
            continue
        lines.append(f"  Turn {index}: expected {_expected_summary(turn)}")
        lines.append(f"  Observed: {_compact_text(_observed_summary(turn))}")
        if turn.failed_checks:
            failures = turn.failed_checks[:MAX_PROMPT_FAILURES_PER_EXAMPLE]
            lines.append(f"  Failed: {'; '.join(failures)}")
            omitted = len(turn.failed_checks) - len(failures)
            if omitted > 0:
                lines.append(f"  Omitted failed check(s): {omitted}")
    if result.failed_checks and all(turn.passed for turn in result.turns):
        failures = result.failed_checks[:MAX_PROMPT_FAILURES_PER_EXAMPLE]
        lines.append(f"  Failed: {'; '.join(failures)}")
    return lines


def _expected_summary(turn) -> str:
    return f"{turn.expectation.action}; searched={turn.expectation.searched}"


def _observed_summary(turn) -> str:
    parts = [
        f"searched={turn.searched}",
        f"agent={_one_line(turn.agent_response)}",
    ]
    if turn.search_call:
        parts.append(f"search={turn.search_call.get('parsed_query')}")
    return "; ".join(parts)


def _flow_order() -> dict[str, int]:
    order: dict[str, int] = {}
    for index, flow in enumerate(FLOWS):
        order.setdefault(flow.issue_key, index)
    return order


def _one_line(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) <= 260:
        return compact
    return compact[:257] + "..."


def _compact_text(value: str, *, limit: int = PROMPT_TEXT_LIMIT) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _sample_flow(issue_key: str):
    for flow in FLOWS:
        if flow.issue_key == issue_key:
            return flow
    return FLOWS[0]
