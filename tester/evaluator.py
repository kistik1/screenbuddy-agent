from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tester.flows import Flow, TurnExpectation


@dataclass
class TurnResult:
    user_input: str
    agent_response: str
    searched: bool
    expectation: TurnExpectation
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    intent: Any = None
    search_call: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return not self.failed_checks


@dataclass
class FlowResult:
    flow: Flow
    turns: list[TurnResult]

    @property
    def status(self) -> str:
        return "PASS" if all(turn.passed for turn in self.turns) else "FAIL"

    @property
    def failed_checks(self) -> list[str]:
        failures: list[str] = []
        for index, turn in enumerate(self.turns, start=1):
            for failure in turn.failed_checks:
                failures.append(f"turn {index}: {failure}")
        return failures


def evaluate_turn(
    user_input: str,
    response: Any,
    expectation: TurnExpectation,
    search_calls: list[dict[str, Any]],
    previous_search_count: int,
) -> TurnResult:
    new_searches = search_calls[previous_search_count:]
    search_call = new_searches[-1] if new_searches else None
    searched = bool(getattr(response, "searched", False)) or bool(new_searches)
    message = str(getattr(response, "message", ""))
    result = TurnResult(
        user_input=user_input,
        agent_response=message,
        searched=searched,
        expectation=expectation,
        intent=getattr(response, "intent", None),
        search_call=search_call,
    )

    if expectation.searched is not None:
        _record(
            result,
            searched is expectation.searched,
            f"searched == {expectation.searched}",
            f"expected searched == {expectation.searched}, got {searched}",
        )

    lowered_message = message.lower()
    for phrase in expectation.contains:
        _record(
            result,
            phrase.lower() in lowered_message,
            f"response contains {phrase!r}",
            f"response missing {phrase!r}",
        )
    if expectation.contains_any:
        passed = any(
            phrase.lower() in lowered_message
            for phrase in expectation.contains_any
        )
        _record(
            result,
            passed,
            f"response contains one of {expectation.contains_any!r}",
            f"response missing any of {expectation.contains_any!r}",
        )
    for phrase in expectation.not_contains:
        _record(
            result,
            phrase.lower() not in lowered_message,
            f"response avoids {phrase!r}",
            f"response unexpectedly contains {phrase!r}",
        )

    for key, expected in expectation.intent.items():
        actual = getattr(result.intent, key, None)
        if isinstance(expected, tuple):
            passed = all(item in (actual or []) for item in expected)
            description = f"intent.{key} includes {expected}"
            failure = f"intent.{key} expected to include {expected}, got {actual!r}"
        else:
            passed = actual == expected
            description = f"intent.{key} == {expected!r}"
            failure = f"intent.{key} expected {expected!r}, got {actual!r}"
        _record(result, passed, description, failure)

    search_query = _search_query(search_call)
    for key, expected in expectation.search.items():
        if key == "query_text_contains":
            actual = str(search_query.get("query_text", "")).lower()
            passed = all(str(item).lower() in actual for item in expected)
            description = f"search.query_text contains {expected}"
            failure = (
                f"search.query_text expected to contain {expected}, "
                f"got {search_query.get('query_text')!r}"
            )
        else:
            actual = search_query.get(key)
            passed = actual == expected
            description = f"search.{key} == {expected!r}"
            failure = f"search.{key} expected {expected!r}, got {actual!r}"
        _record(result, passed, description, failure)

    return result


def _record(
    result: TurnResult,
    passed: bool,
    passed_message: str,
    failed_message: str,
) -> None:
    if passed:
        result.passed_checks.append(passed_message)
    else:
        result.failed_checks.append(failed_message)


def _search_query(search_call: dict[str, Any] | None) -> dict[str, Any]:
    if not search_call:
        return {}
    return dict(search_call.get("parsed_query") or {})
