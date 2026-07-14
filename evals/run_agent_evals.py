from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
AGENT_DIR = ROOT / "agent"
for path in (APP_DIR, AGENT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from service.demo_agent_service import build_demo_response  # noqa: E402

DEFAULT_CASES_PATH = Path(__file__).with_name("agent_routes.json")


def load_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(case: dict[str, Any]) -> list[str]:
    result = build_demo_response(case["query"])
    failures: list[str] = []

    if result.route_agent != case["expected_agent"]:
        failures.append(f"expected agent {case['expected_agent']}, got {result.route_agent}")

    expected_tools = case.get("expected_tools") or []
    if expected_tools and result.tool_name not in expected_tools:
        failures.append(f"expected tool in {expected_tools}, got {result.tool_name}")

    for keyword in case.get("expected_keywords") or []:
        if keyword not in result.answer:
            failures.append(f"missing keyword: {keyword}")

    return failures


def run_evals(cases: list[dict[str, Any]]) -> tuple[int, list[str]]:
    failures: list[str] = []
    for case in cases:
        case_failures = evaluate_case(case)
        if case_failures:
            failures.append(f"{case['id']}: " + "; ".join(case_failures))
    return len(cases) - len(failures), failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Cloud Agent route evals.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    passed, failures = run_evals(cases)
    total = len(cases)
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"Agent route evals: {passed}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
