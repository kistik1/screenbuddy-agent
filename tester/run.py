from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from tester.evaluator import FlowResult, evaluate_turn
from tester.flows import Flow, build_flow_batch
from tester.report import write_report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    original_branch = current_branch(repo_root)

    validate_branch(repo_root, args.branch)
    validate_branch_safety(repo_root, original_branch, args.branch)
    batch_seed = resolve_batch_seed(args.seed)

    try:
        if original_branch != args.branch:
            git(repo_root, "switch", args.branch)
        results = run_flows(
            count=args.count,
            seed=batch_seed,
            client=args.client,
        )
        report_dir = Path(args.report_dir)
        if not report_dir.is_absolute():
            report_dir = repo_root / report_dir
        report_paths = write_report(
            branch=args.branch,
            results=results,
            report_dir=report_dir,
            issue_count=args.issue_count,
            requested_count=args.count,
            batch_seed=batch_seed,
            generation_mode="generated",
        )
    finally:
        if original_branch and current_branch(repo_root) != original_branch:
            git(repo_root, "switch", original_branch)

    passed = sum(1 for result in results if result.status == "PASS")
    failed = len(results) - passed
    print(f"Batch seed: {batch_seed}")
    print(f"Ran {len(results)} flows on branch {args.branch}: {passed} pass, {failed} fail")
    print(f"Issues report: {report_paths.issues}")
    print(f"Details report: {report_paths.details}")
    return 0 if failed == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run user-eye ScreenBuddy conversation flow tests.",
    )
    parser.add_argument("--branch", required=True, help="Git branch to test.")
    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Number of flows to run. Defaults to 30.",
    )
    parser.add_argument(
        "--report-dir",
        default="tester/reports",
        help="Directory for Markdown reports.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Generated batch seed. Omit for a new random batch each run.",
    )
    parser.add_argument(
        "--issue-count",
        type=int,
        default=3,
        help="Number of high-scored summary issues to include. Defaults to 3.",
    )
    parser.add_argument(
        "--client",
        choices=("live", "none"),
        default="live",
        help="LLM client mode. Use 'none' to disable OpenAI-backed calls.",
    )
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.issue_count < 1:
        parser.error("--issue-count must be at least 1")
    return args


def resolve_batch_seed(seed: int | None) -> int:
    if seed is not None:
        return seed
    return random.SystemRandom().randrange(1, 2**31)


def run_flows(
    *,
    count: int = 30,
    seed: int | None = None,
    client: Literal["live", "none"] = "live",
) -> list[FlowResult]:
    flows = selected_flows(count=count, seed=seed)
    results: list[FlowResult] = []
    for index, flow in enumerate(flows, start=1):
        print(f"[{index}/{len(flows)}] {flow.id}")
        results.append(
            run_flow(flow, chat_id=10_000 + index, client=client)
        )
    return results


def selected_flows(*, count: int, seed: int | None = None) -> tuple[Flow, ...]:
    return build_flow_batch(count=count, seed=resolve_batch_seed(seed))


def run_flow(
    flow: Flow,
    *,
    chat_id: int,
    client: Literal["live", "none"] = "live",
) -> FlowResult:
    agent, search_calls = build_agent(client=client)
    turns = []
    for user_input, expectation in zip(flow.user_inputs, flow.expectations):
        previous_search_count = len(search_calls)
        response = agent.handle_message(chat_id, user_input)
        turns.append(
            evaluate_turn(
                user_input=user_input,
                response=response,
                expectation=expectation,
                search_calls=search_calls,
                previous_search_count=previous_search_count,
            )
        )
    return FlowResult(flow=flow, turns=turns)


def build_agent(
    client: Literal["live", "none"] = "live",
) -> tuple[Any, list[dict[str, Any]]]:
    from agent import dialogue_generator, topic_router
    from agent.conversation_state import ConversationSessionStore
    from agent.screenbuddy_agent import ScreenBuddyAgent
    from services import (
        session_intent_analyzer,
        user_state_analyzer,
    )

    if client == "none":
        dialogue_generator.client = None
        topic_router.client = None
        session_intent_analyzer.client = None
        user_state_analyzer.client = None
    search_calls: list[dict[str, Any]] = []

    def fake_search(**kwargs: Any) -> list[dict[str, Any]]:
        search_calls.append(kwargs)
        parsed_query = kwargs.get("parsed_query") or {}
        streaming = parsed_query.get("streaming") or "Netflix"
        content_type = parsed_query.get("type") or "Movie"
        return [
            _recommendation("Easy Match", streaming, content_type, 0.92),
            _recommendation("Second Option", streaming, content_type, 0.84),
            _recommendation("Third Pick", streaming, content_type, 0.78),
        ]

    agent = ScreenBuddyAgent(
        store=ConversationSessionStore(),
        search_fn=fake_search,
        explanation_fn=lambda **kwargs: "This fits the user signals captured so far.",
        search_context={
            "df": object(),
            "vectorizer": object(),
            "tfidf_matrix": object(),
        },
    )
    return agent, search_calls


def validate_clean_tracked_tree(repo_root: Path) -> None:
    status = git(
        repo_root,
        "status",
        "--porcelain",
        "--untracked-files=no",
        capture=True,
    )
    if status.strip():
        raise SystemExit(
            "Tracked working tree changes exist. Commit or stash them before "
            "running branch-based tester on a different branch."
        )


def validate_branch_safety(
    repo_root: Path,
    original_branch: str,
    requested_branch: str,
) -> None:
    if original_branch != requested_branch:
        validate_clean_tracked_tree(repo_root)


def validate_branch(repo_root: Path, branch: str) -> None:
    git(repo_root, "rev-parse", "--verify", branch, capture=True)


def current_branch(repo_root: Path) -> str:
    return git(repo_root, "branch", "--show-current", capture=True).strip()


def git(repo_root: Path, *args: str, capture: bool = False) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr or ""
        raise SystemExit(f"git {' '.join(args)} failed: {stderr.strip()}")
    return completed.stdout or ""


def _recommendation(
    title: str,
    streaming: str,
    content_type: str,
    score: float,
) -> dict[str, Any]:
    return {
        "title": title,
        "genres": "Comedy, Family",
        "description": "Warm, light, and accessible.",
        "type": content_type,
        "release_year": "2024",
        "duration": "90 min",
        "target_audience": "adults",
        "age_category": "recent",
        "streaming": streaming,
        "similarity_score": score,
        "cluster_id": "1",
        "cluster_name": "Comfort",
        "dbscan_cluster": "1",
        "is_outlier": False,
        "more_from_cluster": [],
    }


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    sys.exit(main())
