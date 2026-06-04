from __future__ import annotations

import pytest

from tester.evaluator import evaluate_turn
from tester.flows import FLOWS, TurnExpectation
from tester.report import render_details_report, render_issues_report, write_report
from tester.run import (
    build_agent,
    parse_args,
    resolve_batch_seed,
    selected_flows,
    validate_branch_safety,
)


class Response:
    def __init__(self, message, searched=False, intent=None):
        self.message = message
        self.searched = searched
        self.intent = intent


class Intent:
    genres = ["comedy"]
    avoid_genres = ["horror"]
    language_preference = "spanish"


def test_cli_defaults_to_30_flows():
    args = parse_args(["--branch", "v3"])

    assert args.branch == "v3"
    assert args.count == 30
    assert args.issue_count == 3
    assert args.client == "live"


def test_cli_accepts_custom_issue_count():
    args = parse_args(["--branch", "v3", "--issue-count", "5"])

    assert args.issue_count == 5


def test_cli_accepts_client_none():
    args = parse_args(["--branch", "v3", "--client", "none"])

    assert args.client == "none"


def test_cli_rejects_invalid_client():
    with pytest.raises(SystemExit):
        parse_args(["--branch", "v3", "--client", "fake"])


def test_cli_rejects_zero_issue_count():
    with pytest.raises(SystemExit):
        parse_args(["--branch", "v3", "--issue-count", "0"])


def test_selected_flows_generates_exact_count_and_includes_baseline():
    selected = selected_flows(count=50, seed=123)

    assert len(selected) == 50
    assert selected[:len(FLOWS)] == FLOWS
    assert len({flow.id for flow in selected}) == 50


def test_flows_include_main_goal_category():
    main_goal_flows = [
        flow for flow in FLOWS
        if flow.issue_key == "main_goal"
    ]

    assert main_goal_flows
    assert any("don't know" in " ".join(flow.user_inputs) for flow in main_goal_flows)
    assert any("drained" in " ".join(flow.user_inputs) for flow in main_goal_flows)


def test_selected_flows_is_reproducible_by_seed():
    first = selected_flows(count=50, seed=123)
    second = selected_flows(count=50, seed=123)
    different = selected_flows(count=50, seed=456)

    assert [flow.id for flow in first] == [flow.id for flow in second]
    assert [flow.user_inputs for flow in first] == [flow.user_inputs for flow in second]
    assert [flow.id for flow in first] != [flow.id for flow in different]


def test_selected_flows_small_count_uses_seeded_batch():
    first = selected_flows(count=10, seed=123)
    second = selected_flows(count=10, seed=456)

    assert len(first) == 10
    assert len({flow.id for flow in first}) == 10
    assert [flow.id for flow in first] != [flow.id for flow in second]


def test_resolve_batch_seed_returns_positive_random_seed():
    assert resolve_batch_seed(42) == 42
    assert resolve_batch_seed(None) > 0


def test_branch_safety_allows_dirty_tree_on_current_branch(monkeypatch, tmp_path):
    def fail_if_checked(*args, **kwargs):
        raise AssertionError("same-branch runs should not check git status")

    monkeypatch.setattr("tester.run.validate_clean_tracked_tree", fail_if_checked)

    validate_branch_safety(tmp_path, "v5", "v5")


def test_branch_safety_rejects_dirty_tree_when_switching(monkeypatch, tmp_path):
    def reject_dirty_tree(repo_root):
        raise SystemExit("dirty")

    monkeypatch.setattr("tester.run.validate_clean_tracked_tree", reject_dirty_tree)

    with pytest.raises(SystemExit, match="dirty"):
        validate_branch_safety(tmp_path, "v5", "v4")


def test_branch_safety_allows_clean_tree_when_switching(monkeypatch, tmp_path):
    checked = []

    def accept_clean_tree(repo_root):
        checked.append(repo_root)

    monkeypatch.setattr("tester.run.validate_clean_tracked_tree", accept_clean_tree)

    validate_branch_safety(tmp_path, "v5", "v4")

    assert checked == [tmp_path]


def test_build_agent_none_disables_llm_clients(monkeypatch):
    from agent import dialogue_generator, topic_router
    from services import session_intent_analyzer, user_state_analyzer

    sentinel = object()
    monkeypatch.setattr(dialogue_generator, "client", sentinel)
    monkeypatch.setattr(topic_router, "client", sentinel)
    monkeypatch.setattr(session_intent_analyzer, "client", sentinel)
    monkeypatch.setattr(user_state_analyzer, "client", sentinel)

    build_agent(client="none")

    assert dialogue_generator.client is None
    assert topic_router.client is None
    assert session_intent_analyzer.client is None
    assert user_state_analyzer.client is None


def test_build_agent_live_preserves_llm_clients(monkeypatch):
    from agent import dialogue_generator, topic_router
    from services import session_intent_analyzer, user_state_analyzer

    sentinel = object()
    monkeypatch.setattr(dialogue_generator, "client", sentinel)
    monkeypatch.setattr(topic_router, "client", sentinel)
    monkeypatch.setattr(session_intent_analyzer, "client", sentinel)
    monkeypatch.setattr(user_state_analyzer, "client", sentinel)

    build_agent(client="live")

    assert dialogue_generator.client is sentinel
    assert topic_router.client is sentinel
    assert session_intent_analyzer.client is sentinel
    assert user_state_analyzer.client is sentinel


def test_evaluate_turn_checks_response_search_and_intent():
    result = evaluate_turn(
        user_input="I want comedy",
        response=Response("I found a few. Do these feel right?", True, Intent()),
        expectation=TurnExpectation(
            action="recommend",
            contains=("Do these feel right",),
            searched=True,
            intent={"genres": ("comedy",), "language_preference": "spanish"},
            search={"query_text_contains": ("funny",), "streaming": "netflix"},
        ),
        search_calls=[
            {
                "parsed_query": {
                    "query_text": "tired funny",
                    "streaming": "netflix",
                }
            }
        ],
        previous_search_count=0,
    )

    assert result.passed is True


def test_evaluate_turn_checks_any_allowed_response_phrase():
    result = evaluate_turn(
        user_input="I don't know what I want",
        response=Response("Want something cozy, funny, or exciting?", False),
        expectation=TurnExpectation(
            action="ask_follow_up",
            contains_any=("easygoing", "cozy", "quick watch"),
            searched=False,
        ),
        search_calls=[],
        previous_search_count=0,
    )

    assert result.passed is True
    assert any(
        check.startswith("response contains one of")
        for check in result.passed_checks
    )


def test_evaluate_turn_reports_failures():
    result = evaluate_turn(
        user_input="weather?",
        response=Response("I found a few", True),
        expectation=TurnExpectation(
            action="redirect",
            searched=False,
            not_contains=("I found a few",),
        ),
        search_calls=[{"parsed_query": {"query_text": "weather"}}],
        previous_search_count=0,
    )

    assert result.passed is False
    assert len(result.failed_checks) == 2


def test_issues_report_includes_three_default_issue_prompts():
    flow = FLOWS[0]
    result = evaluate_turn(
        user_input=flow.user_inputs[0],
        response=Response("wrong", False),
        expectation=flow.expectations[0],
        search_calls=[],
        previous_search_count=0,
    )

    report = render_issues_report(
        branch="v3",
        requested_count=50,
        batch_seed=123,
        generation_mode="generated",
        results=[
            type("FlowResult", (), {
                "flow": flow,
                "turns": [result],
                "status": "FAIL",
                "failed_checks": result.failed_checks,
            })()
        ],
    )

    assert "ScreenBuddy Issues Report" in report
    assert "- Requested count: 50" in report
    assert "- Batch seed: 123" in report
    assert "- Generation mode: generated" in report
    assert "## Flow Results" not in report
    issue_headings = [
        line for line in report.splitlines()
        if line.startswith("### ") and line[4:6] in {"1.", "2.", "3."}
    ]
    assert len(issue_headings) == 3
    assert "Score:" in report
    assert "Recommended change:" in report
    assert "Evidence:" in report
    assert "Success criteria:" in report
    assert "Exact Codex prompt:" in report
    assert "```text\nFix ScreenBuddy tester issue" in report
    assert flow.id in report
    assert "response missing 'Want to watch something'" in report
    assert report.index("Exact Codex prompt:") < report.index(flow.summary)


def test_issues_report_caps_prompt_examples():
    flow = FLOWS[0]
    result = evaluate_turn(
        user_input=flow.user_inputs[0],
        response=Response("wrong", False),
        expectation=flow.expectations[0],
        search_calls=[],
        previous_search_count=0,
    )
    flow_result = type("FlowResult", (), {
        "flow": flow,
        "turns": [result],
        "status": "FAIL",
        "failed_checks": result.failed_checks,
    })

    report = render_issues_report(
        branch="v3",
        issue_count=1,
        results=[flow_result() for _ in range(6)],
    )

    assert "2 additional failed flow(s) omitted" in report
    assert report.count(f"- `{flow.id}`:") == 4


def test_issues_report_uses_custom_issue_count():
    flow = FLOWS[0]
    result = evaluate_turn(
        user_input=flow.user_inputs[0],
        response=Response("wrong", False),
        expectation=flow.expectations[0],
        search_calls=[],
        previous_search_count=0,
    )

    report = render_issues_report(
        branch="v3",
        issue_count=2,
        results=[
            type("FlowResult", (), {
                "flow": flow,
                "turns": [result],
                "status": "FAIL",
                "failed_checks": result.failed_checks,
            })()
        ],
    )

    issue_headings = [
        line for line in report.splitlines()
        if line.startswith("### ") and line[4:6] in {"1.", "2."}
    ]
    assert len(issue_headings) == 2


def test_details_report_includes_full_flow_results_without_issue_prompts():
    flow = FLOWS[0]
    result = evaluate_turn(
        user_input=flow.user_inputs[0],
        response=Response("wrong", False),
        expectation=flow.expectations[0],
        search_calls=[],
        previous_search_count=0,
    )

    report = render_details_report(
        branch="v3",
        requested_count=50,
        batch_seed=123,
        generation_mode="generated",
        results=[
            type("FlowResult", (), {
                "flow": flow,
                "turns": [result],
                "status": "FAIL",
                "failed_checks": result.failed_checks,
            })()
        ],
    )

    assert "ScreenBuddy Test Details Report" in report
    assert "- Requested count: 50" in report
    assert "- Batch seed: 123" in report
    assert "- Generation mode: generated" in report
    assert "## Flow Results" in report
    assert f"### FAIL: {flow.id}" in report
    assert flow.summary in report
    assert "Transcript:" in report
    assert "Recommended project fix:" in report
    assert "Exact Codex prompt:" not in report
    assert "## Top Issues To Change Or Fix" not in report


def test_write_report_writes_issues_and_details_files(tmp_path):
    flow = FLOWS[0]
    result = evaluate_turn(
        user_input=flow.user_inputs[0],
        response=Response("wrong", False),
        expectation=flow.expectations[0],
        search_calls=[],
        previous_search_count=0,
    )
    flow_result = type("FlowResult", (), {
        "flow": flow,
        "turns": [result],
        "status": "FAIL",
        "failed_checks": result.failed_checks,
    })()

    paths = write_report(
        branch="v3",
        results=[flow_result],
        report_dir=tmp_path,
        requested_count=1,
        batch_seed=123,
        generation_mode="generated",
    )

    assert paths.issues.exists()
    assert paths.details.exists()
    assert paths.issues.name.startswith("screenbuddy-issues-v3-")
    assert paths.details.name.startswith("screenbuddy-details-v3-")
    assert "ScreenBuddy Issues Report" in paths.issues.read_text(encoding="utf-8")
    assert "ScreenBuddy Test Details Report" in paths.details.read_text(encoding="utf-8")
